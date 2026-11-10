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
import PanelLayout from './panel/PanelLayout.jsx'
import Dashboard from './panel/pages/Dashboard.jsx'
import Levels from './panel/pages/Levels.jsx'
import LessonBuilder from './panel/pages/LessonBuilder.jsx'
import CardsEditor from './panel/pages/CardsEditor.jsx'
import GrammarEditor from './panel/pages/GrammarEditor.jsx'
import TextQuizEditor from './panel/pages/TextQuizEditor.jsx'
import Placeholder from './panel/pages/Placeholder.jsx'

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
        {/* Вход и регистрация — /auth и /auth?mode=register; /login и /register — короткие адреса */}
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/login" element={<Navigate to="/auth" replace />} />
        <Route path="/register" element={<Navigate to="/auth?mode=register" replace />} />
        {/* Админ-панель (макет Figma «Tildes — админ-панель») — только admin / editor */}
        <Route path="/panel" element={<PanelLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="levels" element={<Levels />} />
          <Route path="levels/:code" element={<Levels />} />
          <Route path="lessons/:id" element={<LessonBuilder />} />
          <Route path="lessons/:id/cards" element={<CardsEditor />} />
          <Route path="lessons/:id/grammar" element={<GrammarEditor />} />
          <Route path="lessons/:id/text" element={<TextQuizEditor />} />
          <Route path="listening" element={<Placeholder section="listening" />} />
          <Route path="speaking" element={<Placeholder section="speaking" />} />
          <Route path="writing" element={<Placeholder section="writing" />} />
        </Route>
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
