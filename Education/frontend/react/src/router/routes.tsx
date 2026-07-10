import type { RouteObject } from 'react-router-dom'
import AdminLayout from '@/layouts/AdminLayout'
import UserLayout from '@/layouts/UserLayout'
import LoginPage from '@/pages/login'
import QuestionsPage from '@/pages/admin/questions'
import PapersPage from '@/pages/admin/papers'
import ExamsPage from '@/pages/admin/exams'
import UsersPage from '@/pages/admin/users'
import UserExamPage from '@/pages/user/exam'
import AnswerPage from '@/pages/user/exam/AnswerPage'
import ResultPage from '@/pages/user/exam/ResultPage'
import HistoryPage from '@/pages/user/history'
import NotFoundPage from '@/pages/NotFound'

export const routes: RouteObject[] = [
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/admin',
    element: <AdminLayout />,
    children: [
      { index: true, element: <QuestionsPage /> },
      { path: 'questions', element: <QuestionsPage /> },
      { path: 'papers', element: <PapersPage /> },
      { path: 'exams', element: <ExamsPage /> },
      { path: 'users', element: <UsersPage /> },
    ],
  },
  {
    path: '/user',
    element: <UserLayout />,
    children: [
      { path: 'exam', element: <UserExamPage /> },
      { path: 'exam/:paperId', element: <AnswerPage /> },
      { path: 'exam/result/:examId', element: <ResultPage /> },
      { path: 'history', element: <HistoryPage /> },
    ],
  },
  {
    path: '*',
    element: <NotFoundPage />,
  },
]
