import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MainPage from './pages/MainPage.tsx';
import GamePage from './pages/GamePage.tsx';
import Error404 from './pages/404.tsx';

function Router() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<MainPage />} />
                <Route path="/game/" element={<GamePage />} />
                <Route path="*" element={<Error404 />} />
            </Routes>
        </BrowserRouter>
    )
}

export default Router