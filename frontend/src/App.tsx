import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Landing from './pages/Landing'
import NavBar from './components/navbar'

function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<Landing />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App