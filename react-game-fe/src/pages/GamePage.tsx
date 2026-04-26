import { Autocomplete, Button, TextField, Box, Typography } from "@mui/material"
import { useEffect, useState } from "react";

function GamePage() {
    const [textFieldState, setTextFieldState] = useState<{
        value: string;
        focused: boolean;
        before: string[];
        number: number;
        writing: string;
        options: string[];
        selectValue: string | null;
    }>({value: "", focused: true, before: [], number: 0, writing: "", options: [], selectValue: ""});
    const [testTextState, setTestTextState] = useState<{text: {text: string, color: string}[]}>({text: []});
    const addTestText = (text: string, color: string) => {
        setTestTextState(prev => {return {...prev, text: [...testTextState.text, {text: text, color: color}]}});
    }
    const confirmCommand = () => {
        setTextFieldState((prev) => {return {
            ...prev, value: "", selectValue: "", number: 0, writing: "", options: [],
            before: [textFieldState.value, ...textFieldState.before]
        }});
        const text = textFieldState.value.trimEnd().replaceAll(/\s+/g, " ");
        if (text === "") {
            return;
        } else if (text === "/hello") {
            addTestText("Hello, world!", "");
        } else if (text === "/clear") {
            setTestTextState(prev => {return {...prev, text: []}});
        } else if (text.startsWith("/") && text.split(" ")[0].length > 1) {
            addTestText(`Invalid command: "${text.split(" ")[0].slice(1)}"`, "error");
        } else if (text.startsWith("/")) {
            addTestText("Invalid command", "error");
        } else {
            addTestText(text.trimStart(), "");
        }
    }
    const setOptions = (value: string) => {
        if (value.startsWith("/")) {
            return ["/hello", "/clear"];
        } else {
            return [];
        }
    }
    const updateAutocomplete = (_event: React.SyntheticEvent | null, value: string | null) => {
        if (textFieldState.number === 0) {
            setTextFieldState(prev => {return {...prev, value: value ?? "", writing: value ?? ""}});
        } else {
            setTextFieldState(prev => {return {...prev, value: value ?? ""}});
        }
        setTextFieldState(prev => {return {...prev, options: setOptions(value ?? "")}})
    }
    const keyDownHandler = (event: KeyboardEvent) => {
        if (textFieldState.focused) {
            if (event.key === "Enter") {
                confirmCommand();
            } else if (event.ctrlKey && event.key === "ArrowUp" && textFieldState.number < textFieldState.before.length) {
                setTextFieldState(prev => {return {
                    ...prev,
                    value: textFieldState.before[textFieldState.number],
                    number: textFieldState.number + 1,
                    selectValue: null,
                    options: setOptions(textFieldState.before[textFieldState.number])
                }});
            } else if (event.ctrlKey && event.key === "ArrowDown" && textFieldState.number > 1) {
                setTextFieldState(prev => {return {
                    ...prev,
                    value: textFieldState.before[textFieldState.number - 2],
                    number: textFieldState.number - 1,
                    selectValue: null,
                    options: setOptions(textFieldState.before[textFieldState.number - 2])
                }});
            } else if (event.ctrlKey && event.key === "ArrowDown" && textFieldState.number === 1) {
                setTextFieldState(prev => {return {
                    ...prev,
                    value: textFieldState.writing,
                    number: 0,
                    selectValue: null,
                    options: setOptions(textFieldState.writing)
                }});
            }
        }
    }
    useEffect(() => {
        window.addEventListener("keydown", keyDownHandler);
        return () => window.removeEventListener("keydown", keyDownHandler);
    }, [textFieldState]);
    return (
        <>
            <a href="/" style={{display: "block", marginBottom: "24px"}}>
                <img src="/images/icon.svg" alt="Icon" width={100} height={100} />
            </a>
            {testTextState.text.map(text => <Typography variant="h4" gutterBottom color={text.color}>{text.text}</Typography>)}
            <Box sx={{display: "flex", alignItems: "center", gap: "8px"}}>
                <Autocomplete
                    options={textFieldState.options} onInputChange={updateAutocomplete} inputValue={textFieldState.value}
                    onFocus={() => setTextFieldState(prev => {return {...prev, focused: true}})} autoFocus freeSolo
                    onBlur={() => setTextFieldState(prev => {return {...prev, focused: false}})} value={textFieldState.selectValue}
                    onChange={(_event, value) => setTestTextState(prev => {return {...prev, selectValue: value}})}
                    renderInput={(params) => <TextField {...params} variant="standard" sx={{width: 300}} label="Game" />}
                />
                <Button variant="contained" color="primary" onClick={confirmCommand}>Confirm</Button>
            </Box>
        </>
    )
}

export default GamePage