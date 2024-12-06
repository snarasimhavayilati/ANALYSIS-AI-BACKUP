

export const copyTextToClipboard = (text: string): Promise<void> => {
    if (!navigator.clipboard) {
        return Promise.reject(new Error("Clipboard API not available"));
    }
    return navigator.clipboard
        .writeText(text)
        .then(() => {
            console.log("Text successfully copied to clipboard");
        })
        .catch(err => {
            console.error("Failed to copy text: ", err);
            throw err;
        });
};
