import { BrowserRouter, Routes, Route } from 'react-router-dom'
// import NavBar from './components/navbar'
import Login from './pages/Login'
import Landing from './pages/Landing'
import Signup from './pages/Signup'

function App() {
  return (
    <BrowserRouter>
      {/* <NavBar /> */}
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path='/signup' element={<Signup />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App