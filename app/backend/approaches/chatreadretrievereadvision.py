from typing import Any, Awaitable, Callable, Coroutine, Optional, Union
import os
import logging
import asyncio
from azure.search.documents.aio import SearchClient
from azure.storage.blob.aio import ContainerClient
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionContentPartImageParam,
    ChatCompletionContentPartParam,
    ChatCompletionMessageParam,
)
from openai_messages_token_helper import build_messages, get_token_limit

from approaches.approach import ThoughtStep
from approaches.chatapproach import ChatApproach
from core.authentication import AuthenticationHelper
from core.imageshelper import fetch_image
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatCompletion
from semantic_kernel.connectors.ai.function_call_behavior import FunctionCallBehavior
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.azure_chat_prompt_execution_settings import (
    AzureChatPromptExecutionSettings, OpenAIChatPromptExecutionSettings
)
#from services import Service
#from samples.service_settings import ServiceSettings
from semantic_kernel.planners.function_calling_stepwise_planner import (
    FunctionCallingStepwisePlanner,
    FunctionCallingStepwisePlannerOptions,
)
#from plugins.api_plugin import ApiPlugin


class ChatReadRetrieveReadVisionApproach(ChatApproach):
    """
    A multi-step approach that first uses OpenAI to turn the user's question into a search query,
    then uses Azure AI Search to retrieve relevant documents, and then sends the conversation history,
    original user question, and search results to OpenAI to generate a response.
    """

    def __init__(
        self,
        *,
        search_client: SearchClient,
        blob_container_client: ContainerClient,
        openai_client: AsyncOpenAI,
        auth_helper: AuthenticationHelper,
        chatgpt_model: str,
        chatgpt_deployment: Optional[str],  # Not needed for non-Azure OpenAI
        gpt4v_deployment: Optional[str],  # Not needed for non-Azure OpenAI
        gpt4v_model: str,
        embedding_deployment: Optional[str],  # Not needed for non-Azure OpenAI or for retrieval_mode="text"
        embedding_model: str,
        embedding_dimensions: int,
        sourcepage_field: str,
        content_field: str,
        query_language: str,
        query_speller: str,
        vision_endpoint: str,
        vision_token_provider: Callable[[], Awaitable[str]]
    ):
        self.search_client = search_client
        self.blob_container_client = blob_container_client
        self.openai_client = openai_client
        self.auth_helper = auth_helper
        self.chatgpt_model = chatgpt_model
        self.chatgpt_deployment = chatgpt_deployment
        self.gpt4v_deployment = gpt4v_deployment
        self.gpt4v_model = gpt4v_model
        self.embedding_deployment = embedding_deployment
        self.embedding_model = embedding_model
        self.embedding_dimensions = embedding_dimensions
        self.sourcepage_field = sourcepage_field
        self.content_field = content_field
        self.query_language = query_language
        self.query_speller = query_speller
        self.vision_endpoint = vision_endpoint
        self.vision_token_provider = vision_token_provider
        self.chatgpt_token_limit = get_token_limit(gpt4v_model)

    @property
    def system_message_chat_conversation(self):
        return """You are an experienced and highly analytical Equity Analyst specializing in the automotive and airline industries. Your role is to evaluate the financial health, market trends, and growth potential of publicly traded companies within these sectors. You conduct in-depth research, build financial models, and provide actionable investment recommendations to portfolio managers, institutional clients, or other stakeholders.

            Key points to consider:
            1. Analyze financial statements, including income statements, balance sheets, and cash flow statements, to assess a company's financial performance and health.
            2. Evaluate market trends, competitive dynamics, and regulatory environments impacting the automotive and airline industries.
            3. Build and maintain financial models to forecast future earnings, cash flows, and valuations.
            4. Provide insights on industry-specific metrics, such as fleet utilization, load factors, and revenue per available seat mile (RASM) for airlines, or production volumes, sales figures, and market share for automotive companies.
            5. Assess the impact of macroeconomic factors, such as interest rates, fuel prices, and economic cycles, on the industries.
            6. Identify and analyze potential risks and opportunities, including technological advancements, regulatory changes, and geopolitical events.
            7. Offer recommendations on buy, hold, or sell decisions based on comprehensive analysis and valuation methods.
            
            When analyzing documents:
            - Each image source has the file name in the top left corner (coordinates 10,10) and bottom left corner (coordinates 10,780) in the format SourceFileName:<file_name>
            - Cite sources as [<filename>#page=specific page number] for each fact used, clearly indicating the specific page number from which the content was referred.
            - Text sources begin on a new line with the file name, followed by a colon and the information.
            - Use only the provided sources to answer questions.
            - Present tabular data in HTML format, not markdown.
            - If clarification is needed, ask concise, relevant questions.
            - If the information is not in the sources, state that you don't have sufficient information to answer.
            - If the question asked is "Please list all the companies available in the system?" , list these company names with categories: **Technology Companies:** GOOG: Alphabet Inc., NVDA: NVIDIA Corporation, AAPL: Apple Inc., META: Meta Platforms, Inc., MSFT: Microsoft Corporation, AMZN: Amazon.com, Inc. **Airline Companies:** AAL: American Airlines Group, DAL: Delta Air Lines, UAL: United Airlines Holdings, LUV: Southwest Airlines, ALK: Alaska Air Group, JBLU: JetBlue Airways, SAVE: Spirit Airlines, ULCC: Frontier Airlines Holdings, HA: Hawaiian Holdings, ALGT: Allegiant Travel **Automotive Companies:** CVNA: Carvana Co., TSLA: Tesla Inc., F: Ford Motor Company, GM: General Motors, STLA: Stellantis N.V., RIVN: Rivian Automotive, LCID: Lucid Group, RIDE: Lordstown Motors, PII: Polaris Inc., TM: Toyota Motor Corporation, HMC: Honda Motor Co., Ltd. Also, make sure not to refer to any other document or file.

            Approach your responses as a regulatory authority would:
            - Prioritize accuracy, thorough analysis, and actionable insights in your advice.
            - If you have a choice between company reports and market analysis reports, give priority to the company reports.
            - Highlight potential risks and opportunities affecting the company's financial performance and market position.
            - Suggest steps for further analysis or areas that require deeper investigation where applicable.
            - Be concise but comprehensive in your explanations.

            {follow_up_questions_prompt}
            {injected_prompt}"""

    async def run_until_final_call(
        self,
        messages: list[ChatCompletionMessageParam],
        overrides: dict[str, Any],
        auth_claims: dict[str, Any],
        should_stream: bool = False,
    ) -> tuple[dict[str, Any], Coroutine[Any, Any, Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]]]:
        use_text_search = overrides.get("retrieval_mode") in ["text", "hybrid", None]
        use_vector_search = overrides.get("retrieval_mode") in ["vectors", "hybrid", None]
        use_semantic_ranker = True if overrides.get("semantic_ranker") else False
        use_semantic_captions = True if overrides.get("semantic_captions") else False
        top = overrides.get("top", 3)
        minimum_search_score = overrides.get("minimum_search_score", 0.0)
        minimum_reranker_score = overrides.get("minimum_reranker_score", 0.0)
        filter = self.build_filter(overrides, auth_claims)

        vector_fields = overrides.get("vector_fields", ["embedding"])
        send_text_to_gptvision = overrides.get("gpt4v_input") in ["textAndImages", "texts", None]
        send_images_to_gptvision = overrides.get("gpt4v_input") in ["textAndImages", "images", None]

        original_user_query = messages[-1]["content"]
        if not isinstance(original_user_query, str):
            raise ValueError("The most recent message content must be a string.")
        past_messages: list[ChatCompletionMessageParam] = messages[:-1]

        # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
        user_query_request = "Generate search query for: " + original_user_query

        query_response_token_limit = 100
        # query_model = self.chatgpt_model
        # query_deployment = self.chatgpt_deployment
        query_model = self.gpt4v_model
        query_deployment = self.gpt4v_deployment
        query_messages = build_messages(
            model=query_model,
            system_prompt=self.query_prompt_template,
            few_shots=self.query_prompt_few_shots,
            past_messages=past_messages,
            new_user_content=user_query_request,
            max_tokens=self.chatgpt_token_limit - query_response_token_limit,
        )
        print("Tokens used")
        print(self.chatgpt_token_limit)
        chat_completion: ChatCompletion = await self.openai_client.chat.completions.create(
            model=query_deployment if query_deployment else query_model,
            messages=query_messages,
            temperature=0.0,  # Minimize creativity for search query generation
            max_tokens=query_response_token_limit,
            n=1,
        )

        query_text = self.get_search_query(chat_completion, original_user_query)
        
        # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query

        # If retrieval mode includes vectors, compute an embedding for the query
        vectors = []
        if use_vector_search:
            for field in vector_fields:
                vector = (
                    await self.compute_text_embedding(query_text)
                    if field == "embedding"
                    else await self.compute_image_embedding(query_text)
                )
                vectors.append(vector)

        results = await self.search(
            top,
            query_text,
            filter,
            vectors,
            use_text_search,
            use_vector_search,
            use_semantic_ranker,
            use_semantic_captions,
            minimum_search_score,
            minimum_reranker_score,
        )
        sources_content = self.get_sources_content(results, use_semantic_captions, use_image_citation=True)
        content = "\n".join(sources_content)
            
        # STEP 3: Generate a contextual and content specific answer using the search results and chat history

        # Allow client to replace the entire prompt, or to inject into the existing prompt using >>>
        system_message = self.get_system_prompt(
            overrides.get("prompt_template"),
            self.follow_up_questions_prompt_content if overrides.get("suggest_followup_questions") else "",
        )

        user_content: list[ChatCompletionContentPartParam] = [{"text": original_user_query, "type": "text"}]
        image_list: list[ChatCompletionContentPartImageParam] = []

        if send_text_to_gptvision:
            user_content.append({"text": "\n\nSources:\n" + content, "type": "text"})
        if send_images_to_gptvision:
            for result in results:
                url = await fetch_image(self.blob_container_client, result)
                if url:
                    image_list.append({"image_url": url, "type": "image_url"})
            user_content.extend(image_list)

        response_token_limit = 1024
        messages = build_messages(
            model=self.chatgpt_model,
            system_prompt=system_message,
            past_messages=messages[:-1],
            # Model does not handle lengthy system messages well. Moving sources to latest user conversation to solve follow up questions prompt.
            #new_user_content=original_user_query + "\n\nSources:\n" + content,
            new_user_content=(
            f"{original_user_query}\n\n"
            "Important: First, neglect the Semantic Kernel Answer. "
            f"Additional Sources:\n{content}"
        ),
            max_tokens=self.chatgpt_token_limit - response_token_limit,
        )

        data_points = {
            "text": sources_content,
            "images": [d["image_url"] for d in image_list],
        }

        extra_info = {
            "data_points": data_points,
            "thoughts": [
                ThoughtStep(
                    "Prompt to generate search query",
                    [str(message) for message in query_messages],
                    (
                        {"model": query_model, "deployment": query_deployment}
                        if query_deployment
                        else {"model": query_model}
                    ),
                ),
                ThoughtStep(
                    "Search using generated search query",
                    query_text,
                    {
                        "use_semantic_captions": use_semantic_captions,
                        "use_semantic_ranker": use_semantic_ranker,
                        "top": top,
                        "filter": filter,
                        "vector_fields": vector_fields,
                        "use_text_search": use_text_search,
                    },
                ),
                ThoughtStep(
                    "Search results",
                    [result.serialize_for_results() for result in results],
                ),
                ThoughtStep(
                    "Prompt to generate answer",
                    [str(message) for message in messages],
                    (
                        {"model": self.gpt4v_model, "deployment": self.gpt4v_deployment}
                        if self.gpt4v_deployment
                        else {"model": self.gpt4v_model}
                    ),
                ),
            ],
        }

        chat_coroutine = self.openai_client.chat.completions.create(
            model=self.gpt4v_deployment if self.gpt4v_deployment else self.gpt4v_model,
            messages=messages,
            temperature=overrides.get("temperature", 0.3),
            max_tokens=response_token_limit,
            n=1,
            stream=should_stream,
        )
        return (extra_info, chat_coroutine)