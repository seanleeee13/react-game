import { Button } from "@mui/material"

function MainPage() {
    return (
        <>
            <a href="/"><img src="/icon.svg" alt="Icon" width={100} height={100} /></a>
            <h1>React Game</h1>
            <Button variant="contained" color="primary" href="/game/">Start Game</Button>
        </>
    )
}

export default MainPage