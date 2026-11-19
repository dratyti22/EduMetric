export type SubjectId =
  | 'math_profile'
  | 'math_base'
  | 'russian'
  | 'physics'
  | 'informatics'
  | 'social'
  | 'chemistry'
  | 'biology'
  | 'history'
  | 'english'

export type UserRole = string
export type ExamStatus = 'draft' | 'in_progress' | 'completed'

export interface SubjectInfo {
  id: SubjectId
  name: string
  defaultTasksCount: number
  defaultMaxScores: number[]
  conversionScale: Record<number, number>
}

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  middle_name?: string | null
  role: UserRole
  position?: string
  subject?: string
  school?: string
  bio?: string
  phone?: string
  firstName: string
  lastName: string
  middleName?: string | null
  name?: string
}

export interface RegisterData {
  email: string
  password: string
  password_confirm: string
  first_name: string
  last_name: string
  middle_name?: string
  role: UserRole
}

export interface Student {
  id: string
  first_name: string
  last_name: string
  middle_name?: string | null
  school_class: string
  is_linked: boolean
  created_at: string
  fullName: string
  userId?: string
}

export interface SchoolClass {
  id: string
  name: string
  number: string | number
  letter: string
  subject: SubjectId
  teacher?: string
  join_code?: string | null
  students_count?: number
  created_at: string
}

export interface ClassJoinRequest {
  id: string
  school_class: string
  class_name: string
  user: string
  user_email: string
  user_name: string
  matched_student: string
  matched_student_name: string
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
}

export interface JoinClassResult {
  status: 'joined' | 'already_member' | 'pending'
  school_class: Pick<SchoolClass, 'id' | 'name' | 'subject' | 'created_at'>
  student?: Student
  request?: ClassJoinRequest
}

export interface TaskSpec {
  taskNumber: number
  maxScore: number
}

export interface ExamTask {
  id: string
  number: number
  max_score: number
  taskNumber: number
  maxScore: number
}

export interface Exam {
  id: string
  title: string
  source: string
  variant: string
  school_class: string
  school_class_name: string
  classId: string
  className: string
  template: string | null
  subject: SubjectId
  academic_year: string
  date: string
  status: ExamStatus
  passing_score_secondary: number
  use_proportional_conversion: boolean
  task_count: number
  max_primary_score: number
  tasks: ExamTask[]
  created_at: string
  updated_at: string
  academicYear: string
  passingScoreSecondary: number
  maxPrimaryScore: number
  createdAt: string
}

export type MockTest = Exam

export interface MockTestResultSheet {
  id: string
  mockTestId: string
  studentScores: Record<string, { studentId: string; scores: Record<number, number>; primaryScore: number; secondaryScore: number }>
  updatedAt: string
}

export interface ExamTemplate {
  id: string
  subject: SubjectId
  year: number
  title: string
  default_passing_secondary: number
  task_count: number
  max_primary_score: number
  tasks: ExamTask[]
}

export interface TaskResult {
  id: string
  task_id: string
  task_number: number
  max_score: number
  score: number | null
}

export interface StudentResult {
  id: string
  student_id: string
  student_name: string
  task_results: TaskResult[]
  scores_by_number: Record<number, number>
  summary: {
    primary_score: number
    secondary_score: number | null
    max_primary_score: number
    is_complete: boolean
  }
}

export interface AnalyticsTask {
  task_number: number
  max_score: number
  avg_score: number
  percent: number
}

export interface ClassAnalyticsSummary {
  total_students: number
  attended_students: number
  avg_primary: number
  avg_secondary: number
  max_secondary: number
  min_secondary: number
  passing_threshold: number
  passed_count: number
  passed_percent: number
  high_achievers_count: number
  high_achievers_percent: number
  score_distribution: { range: string; count: number; percent: number }[]
  task_solvability: AnalyticsTask[]
  totalStudents: number
  attendedStudents: number
  avgPrimary: number
  avgSecondary: number
  maxSecondary: number
  minSecondary: number
  passingThreshold: number
  passedCount: number
  passedPercent: number
  highAchieversCount: number
  highAchieversPercent: number
  scoreDistribution: { range: string; count: number; percent: number }[]
  taskSolvability: { taskNumber: number; maxScore: number; avgScore: number; percent: number }[]
}

export interface ClassDynamicsItem {
  exam_id: string
  title: string
  date: string
  subject: SubjectId
  avg_primary: number
  avg_secondary: number
  attended_students: number
  passed_percent: number
  max_primary_score: number
}

export interface StudentHistoryItem {
  test_id: string
  title: string
  date: string
  subject: SubjectId
  primary_score: number
  secondary_score: number | null
  max_primary_score: number
  scores: Record<number, number>
  is_complete: boolean
  testId: string
  primaryScore: number
  secondaryScore: number
  maxPrimaryScore: number
}
