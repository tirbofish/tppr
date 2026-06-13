import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Login from './pages/Login'
import Landing from './pages/Landing'
import Signup from './pages/Signup'
import { AuthProvider } from './api/auth'
import { Toaster } from '@/components/ui/sonner'
import { TooltipProvider } from '@/components/ui/tooltip'
import PaperEditor from './pages/PaperEditor'
import { PapersViewer } from './pages/PaperEditorViewer'
import Unauthorized from './pages/Unauthorised'
import { GenericError } from './pages/GenericError'
import Search from './pages/Search'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
      <TooltipProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path='/signup' element={<Signup />} />
        <Route path="/papers/:id" element={<PaperEditor />} />
        <Route path="/papers" element={<PapersViewer />} />
        <Route path="/unauthorized" element={<Unauthorized />} />
        <Route path="/search" element={<Search />} />

        {/* always keep this at the bottom */}
        <Route path="*" element={<GenericError code={404} title="Not Found" message="The page you're looking for doesn't exist." />} />
      </Routes>
      <Toaster />
      </TooltipProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
