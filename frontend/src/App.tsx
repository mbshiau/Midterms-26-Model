import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ElectionTypePage } from "./pages/ElectionTypePage";
import { MapPage } from "./pages/MapPage";
import { StateForecastPage } from "./pages/StateForecastPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ElectionTypePage />} />
        <Route path="/governors" element={<MapPage office="Governor" />} />
        <Route path="/senate" element={<MapPage office="Senate" />} />
        <Route path="/states/:slug" element={<StateForecastPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
