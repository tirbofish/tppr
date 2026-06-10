import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Login from './pages/Login'
import Landing from './pages/Landing'
import Signup from './pages/Signup'
import { AuthProvider } from './api/auth'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
      <TooltipProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path='/signup' element={<Signup />} />
      </Routes>
      <Toaster />
      </TooltipProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
