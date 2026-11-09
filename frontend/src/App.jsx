import { useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import Landing from './pages/Landing.jsx'
import Soon from './pages/Soon.jsx'
import Home from './pages/Home.jsx'
import CardsHub from './pages/CardsHub.jsx'
import CardSession from './pages/CardSession.jsx'
import TopicsList from './pages/TopicsList.jsx'
import TopicDetail from './pages/TopicDetail.jsx'
import Rating from './pages/Rating.jsx'
import RequireAuth from './components/RequireAuth.jsx'
import AuthPage from './pages/AuthPage.jsx'

function ScrollToTop() {
  const { pathname, hash } = useLocation()
  useEffect(() => {
    if (!hash) window.scrollTo(0, 0)
  }, [pathname, hash])
  return null
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/login" element={<AuthPage mode="login" />} />
        <Route path="/register" element={<AuthPage mode="register" />} />
        <Route element={<RequireAuth />}>
          <Route path="/" element={<Landing />} />
          <Route path="/soon/:level" element={<Soon />} />
          <Route element={<Layout />}>
            <Route path="/home" element={<Home />} />
            <Route path="/cards" element={<CardsHub />} />
            <Route path="/cards/review" element={<CardSession review />} />
            <Route path="/cards/:id" element={<CardSession />} />
            <Route path="/topics" element={<TopicsList />} />
            <Route path="/topics/:id" element={<TopicDetail />} />
            <Route path="/rating" element={<Rating />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}
