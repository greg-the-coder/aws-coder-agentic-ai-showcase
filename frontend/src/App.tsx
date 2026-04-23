import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ChatPanel from './components/Chat/ChatPanel';
import PortfolioDashboard from './components/Dashboard/PortfolioDashboard';
import WorkatoPanel from './components/MockServices/WorkatoPanel';
import ArizePanel from './components/MockServices/ArizePanel';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<ChatPanel />} />
          <Route path="/dashboard" element={<PortfolioDashboard />} />
          <Route path="/workato" element={<WorkatoPanel />} />
          <Route path="/arize" element={<ArizePanel />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
