import { useMemo } from "react";
import { Stack, IconButton } from "@fluentui/react";
import DOMPurify from "dompurify";

import styles from "./Answer.module.css";
import { ChatAppResponse, getCitationFilePath } from "../../api";
import { parseAnswerToHtml } from "./AnswerParser";
import { AnswerIcon } from "./AnswerIcon";
import { SpeechOutputBrowser } from "./SpeechOutputBrowser";
import { SpeechOutputAzure } from "./SpeechOutputAzure";
import { copyTextToClipboard } from "../../utils";
interface Props {
    answer: ChatAppResponse;
    isSelected?: boolean;
    isStreaming: boolean;
    onCitationClicked: (filePath: string) => void;
    onThoughtProcessClicked: () => void;
    onSupportingContentClicked: () => void;
    onFollowupQuestionClicked?: (question: string) => void;
    showFollowupQuestions?: boolean;
    showSpeechOutputBrowser?: boolean;
    showSpeechOutputAzure?: boolean;
    speechUrl: string | null;
    question: string;
}

export const Answer = ({
    answer,
    question,
    isSelected,
    isStreaming,
    onCitationClicked,
    onThoughtProcessClicked,
    onSupportingContentClicked,
    onFollowupQuestionClicked,
    showFollowupQuestions,
    showSpeechOutputAzure,
    showSpeechOutputBrowser,
    speechUrl
}: Props) => {
    const followupQuestions = answer.context?.followup_questions;
    const messageContent = answer.message.content;
    const parsedAnswer = useMemo(() => parseAnswerToHtml(messageContent, isStreaming, onCitationClicked), [answer]);

    const sanitizedAnswerHtml = DOMPurify.sanitize(parsedAnswer.answerHtml);

    const sendFeedback = (isPositive: boolean) => {
        const subject = encodeURIComponent(`Chatbot Feedback: ${isPositive ? "Good" : "Bad"}`);
        const body = encodeURIComponent(`Feedback: ${isPositive ? "Good" : "Bad"}\n\nQuestion: ${question}\n\nAnswer: ${answer.message.content}`);

        const gmailComposeUrl = `https://mail.google.com/mail/?view=cm&fs=1&to=feedback@flatironsai.com&su=${subject}&body=${body}`;

        window.open(gmailComposeUrl, "_blank");
    };

    const handleCopy = () => {
        const textToCopy = answer.message.content.replace(/\[\^\d+?\]/g, "");
        copyTextToClipboard(textToCopy);
    };

    return (
        <Stack className={`${styles.answerContainer} ${isSelected && styles.selected}`} verticalAlign="space-between">
            <Stack.Item>
                <Stack horizontal horizontalAlign="space-between">
                    <AnswerIcon />
                    <div>
                        {/* <IconButton
                            style={{ color: "green" }}
                            iconProps={{ iconName: "Like" }}
                            title="Thumbs up"
                            ariaLabel="Thumbs up"
                            onClick={() => sendFeedback(true)}
                        />
                        <IconButton
                            style={{ color: "red" }}
                            iconProps={{ iconName: "Dislike" }}
                            title="Thumbs down"
                            ariaLabel="Thumbs down"
                            onClick={() => sendFeedback(false)}
                        /> */}
                        <IconButton
                            style={{ color: "black" }}
                            iconProps={{ iconName: "Copy" }}
                            title="Copy answer"
                            ariaLabel="Copy answer"
                            onClick={handleCopy}
                        />
                        {/* <IconButton
                            style={{ color: "black" }}
                            iconProps={{ iconName: "Lightbulb" }}
                            title="Show thought process"
                            ariaLabel="Show thought process"
                            onClick={() => onThoughtProcessClicked()}
                            disabled={!answer.context.thoughts?.length}
                        /> */}
                        <IconButton
                            style={{ color: "black" }}
                            iconProps={{ iconName: "ClipboardList" }}
                            title="Show supporting content"
                            ariaLabel="Show supporting content"
                            onClick={() => onSupportingContentClicked()}
                            disabled={!answer.context.data_points}
                        />
                        {showSpeechOutputAzure && <SpeechOutputAzure url={speechUrl} />}
                        {showSpeechOutputBrowser && <SpeechOutputBrowser answer={sanitizedAnswerHtml} />}
                    </div>
                </Stack>
            </Stack.Item>

            <Stack.Item grow>
                <div className={styles.answerText} dangerouslySetInnerHTML={{ __html: sanitizedAnswerHtml }}></div>
            </Stack.Item>

            {!!parsedAnswer.citations.length && (
                <Stack.Item>
                    <Stack horizontal wrap tokens={{ childrenGap: 5 }}>
                        <span className={styles.citationLearnMore}>Citations:</span>
                        {parsedAnswer.citations.map((x, i) => {
                            const path = getCitationFilePath(x);
                            return (
                                <a key={i} className={styles.citation} title={x} onClick={() => onCitationClicked(path)}>
                                    {`${++i}. ${x}`}
                                </a>
                            );
                        })}
                    </Stack>
                </Stack.Item>
            )}

            {!!followupQuestions?.length && showFollowupQuestions && onFollowupQuestionClicked && (
                <Stack.Item>
                    <Stack horizontal wrap className={`${!!parsedAnswer.citations.length ? styles.followupQuestionsList : ""}`} tokens={{ childrenGap: 6 }}>
                        <span className={styles.followupQuestionLearnMore}>Follow-up questions:</span>
                        {followupQuestions.map((x, i) => {
                            return (
                                <a key={i} className={styles.followupQuestion} title={x} onClick={() => onFollowupQuestionClicked(x)}>
                                    {`${x}`}
                                </a>
                            );
                        })}
                    </Stack>
                </Stack.Item>
            )}
        </Stack>
    );
};
