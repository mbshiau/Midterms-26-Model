import { BrowserRouter, Route, Routes } from "react-router-dom";
import { MapPage } from "./pages/MapPage";
import { StateForecastPage } from "./pages/StateForecastPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MapPage />} />
        <Route path="/states/:stateCode"  element={<StateForecastPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
