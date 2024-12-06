import { Outlet, NavLink, Link } from "react-router-dom";

import github from "../../assets/github.svg";

import styles from "./Layout.module.css";

import { useLogin } from "../../authConfig";

import { LoginButton } from "../../components/LoginButton";

import logo from "../../assets/flatirons.png";
import { useState, useEffect } from "react";
import { getUsername } from "../../authConfig";
import { useMsal } from "@azure/msal-react";
import { IconButton } from "@fluentui/react";

const Layout = () => {
    const { instance } = useMsal();
    const [username, setUsername] = useState("");
    useEffect(() => {
        const fetchUsername = async () => {
            setUsername((await getUsername(instance)) ?? "");
        };

        fetchUsername();
    }, []);

    const handleDownload = () => {
        const htmlContent = document.documentElement.outerHTML;
        const blob = new Blob([htmlContent], { type: "text/html" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "page_content.html";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    return (
        <div className={styles.layout}>
            <header className={styles.header} role={"banner"}>
                <div className={styles.headerContainer}>
                    <Link to="/" className={styles.headerTitleContainer}>
                        {/* <h3 className={styles.headerTitle}>GPT + Enterprise data | Sample</h3> */}
                        <img src={logo} alt="Logo" className={styles.headerLogo} />
                    </Link>
                    {/* <nav>
                        <ul className={styles.headerNavList}>
                            
                            <li className={styles.headerNavLeftMargin}>
                                <a href="https://flatironsai.com/enterprise-copilot/" target="_blank" rel="noopener noreferrer">
                                    <button className={styles.navButton}>Learn About Copilot Enterprise</button>
                                </a>
                            </li>
                            <li className={styles.headerNavLeftMargin}>
                                <a href="https://flatironsai.com/useful-tips/" target="_blank" rel="noopener noreferrer">
                                    {<button className={styles.navButton}>Useful Tips</button>}
                                </a>
                            </li>
                            <li className={styles.headerNavLeftMargin}>
                                <a href="https://flatironsai.com/beta-feedback/" target="_blank" rel="noopener noreferrer">
                                    {<button className={styles.navButton}>Feedback?</button>}
                                </a>
                            </li>
                        </ul>
                    </nav> */}
                    {/* <div className={styles.headerRight}>
                        {username && <span className={styles.welcomeMessage}>Hello, {username}</span>}
                        {useLogin && <LoginButton />}
                    </div> */}
                    <div className={styles.headerRight}>{useLogin && <LoginButton />}</div>
                </div>
            </header>

            <Outlet />
            <footer className={styles.footer} role={"contentinfo"}>
                {/* <IconButton
                    iconProps={{ iconName: "Download" }}
                    title="Download Page"
                    ariaLabel="Download Page"
                    onClick={handleDownload}
                    className={styles.downloadButton}
                /> */}
                {/* <a href="https://flatironsai.com/beta-feedback/" target="_blank" rel="noopener norefererrer">
                    <button className={styles.footerButton}>Feedback?</button>
                </a> */}
            </footer>
        </div>
    );
};

export default Layout;
