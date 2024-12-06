import { Example } from "./Example";

import styles from "./Example.module.css";

const DEFAULT_EXAMPLES: string[] = [
    "Which airlines are achieving their 2024 objectives?",
    "Explain Tesla's margin compression in 2024.",
    "What is Ford's strategy for electric vehicles?",
    "Please list all the companies available in the system?"
];

const GPT4V_EXAMPLES: string[] = [
    "Which airlines are achieving their 2024 objectives?",
    "Explain Tesla's margin compression in 2024.",
    "What is Ford's strategy for electric vehicles?",
    "Please list all the companies available in the system?"
];

interface Props {
    onExampleClicked: (value: string) => void;
    useGPT4V?: boolean;
}

export const ExampleList = ({ onExampleClicked, useGPT4V }: Props) => {
    return (
        <ul className={styles.examplesNavList}>
            {(useGPT4V ? GPT4V_EXAMPLES : DEFAULT_EXAMPLES).map((question, i) => (
                <li key={i}>
                    <Example text={question} value={question} onClick={onExampleClicked} />
                </li>
            ))}
        </ul>
    );
};
