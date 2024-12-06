import { renderToStaticMarkup } from "react-dom/server";
import { getCitationFilePath } from "../../api";
import React from "react";

type HtmlParsedAnswer = {
    answerHtml: string;
    citations: string[];
};

function replaceBoldSyntax(text: string): JSX.Element[] {
    const parts = text.split(/\*\*(.*?)\*\*/g);
    return parts.map((part, index) => {
        if (index % 2 === 0) {
            return <React.Fragment key={index}>{part}</React.Fragment>;
        } else {
            return <b key={index}>{part}</b>;
        }
    });
}

function convertHeadingsToBold(text: string): string {
    return text
        .split("\n")
        .map(line => {
            if (line.startsWith("#")) {
                // Remove '#' symbols and trim, then wrap with '**'
                return `**${line.replace(/^#+\s*/, "").trim()}**`;
            }
            return line;
        })
        .join("\n");
}

export function parseAnswerToHtml(answer: string, isStreaming: boolean, onCitationClicked: (citationFilePath: string) => void): HtmlParsedAnswer {
    const citations: string[] = [];

    // Convert headings to bold and trim any whitespace
    let parsedAnswer = convertHeadingsToBold(answer).trim();

    console.log("Entered Parser");
    console.log("Processed Answer:", parsedAnswer);

    // Omit a citation that is still being typed during streaming
    if (isStreaming) {
        let lastIndex = parsedAnswer.length;
        for (let i = parsedAnswer.length - 1; i >= 0; i--) {
            if (parsedAnswer[i] === "]") {
                break;
            } else if (parsedAnswer[i] === "[") {
                lastIndex = i;
                break;
            }
        }
        const truncatedAnswer = parsedAnswer.substring(0, lastIndex);
        parsedAnswer = truncatedAnswer;
        console.log("Truncated Answer:", parsedAnswer);
    }

    const parts = parsedAnswer.split(/\[([^\]]+)\]/g);

    const fragments = parts.map((part, index) => {
        if (index % 2 === 0) {
            return replaceBoldSyntax(part);
        } else {
            let citationIndex: number;
            if (citations.indexOf(part) !== -1) {
                citationIndex = citations.indexOf(part) + 1;
            } else {
                citations.push(part);
                citationIndex = citations.length;
            }

            const path = getCitationFilePath(part);

            return (
                <React.Fragment key={index}>
                    {" "}
                    <a className="supContainer" title={part} onClick={() => onCitationClicked(path)}>
                        <sup>{citationIndex}</sup>
                    </a>
                </React.Fragment>
            );
        }
    });

    return {
        answerHtml: renderToStaticMarkup(<>{fragments}</>),
        citations
    };
}
