import { Button } from "@mui/material"

function Error404() {
    return (
        <>
            <a href="/"><img src="/icon.svg" alt="Icon" width={100} height={100} /></a>
            <h1>404 Not Found</h1>
            <Button variant="contained" color="primary" href="/">Back to Home</Button>
        </>
    )
}

export default Error404