import { BrowserRouter, Routes, Route } from 'react-router-dom'
// import NavBar from './components/navbar'
import Login from './pages/Login'
import Landing from './pages/Landing'
import Signup from './pages/Signup'
import { AuthProvider } from './api/auth'

function App() {
  return (
    <BrowserRouter>
      {/* <NavBar /> */}
      <AuthProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path='/signup' element={<Signup />} />
      </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App