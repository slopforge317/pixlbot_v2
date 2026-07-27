import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { TelegramProvider, UserProvider, ProvidersProvider } from './contexts'
import GeneratePage from './pages/GeneratePage'
import HistoryPage from './pages/HistoryPage'
import PackagesPage from './pages/PackagesPage'

function App() {
  return (
    <BrowserRouter>
      <TelegramProvider>
        <UserProvider>
          <ProvidersProvider>
            <Routes>
              <Route path="/" element={<GeneratePage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/packages" element={<PackagesPage />} />
            </Routes>
          </ProvidersProvider>
        </UserProvider>
      </TelegramProvider>
    </BrowserRouter>
  )
}

export default App
