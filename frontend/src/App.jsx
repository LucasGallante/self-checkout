import { BrowserRouter, Routes, Route } from 'react-router-dom';
import CustomerFlow from './pages/CustomerFlow.jsx';
import Admin from './pages/Admin.jsx';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<CustomerFlow />} />
        <Route path="/admin" element={<Admin />} />
      </Routes>
    </BrowserRouter>
  );
}
