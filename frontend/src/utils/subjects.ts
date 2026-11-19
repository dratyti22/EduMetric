import type { SubjectId } from '../types'

export const SUBJECTS: { id: SubjectId; name: string }[] = [
  { id: 'math_profile', name: 'Математика (профиль)' },
  { id: 'math_base', name: 'Математика (база)' },
  { id: 'russian', name: 'Русский язык' },
  { id: 'informatics', name: 'Информатика' },
  { id: 'physics', name: 'Физика' },
  { id: 'social', name: 'Обществознание' },
  { id: 'biology', name: 'Биология' },
  { id: 'chemistry', name: 'Химия' },
  { id: 'history', name: 'История' },
  { id: 'english', name: 'Английский язык' },
]

export function subjectId(value: string): SubjectId {
  return SUBJECTS.find((item) => item.id === value || item.name === value)?.id || (value as SubjectId)
}

export function subjectLabel(value: string): string {
  return SUBJECTS.find((item) => item.id === value)?.name || value
}

export function subjectName(id: string): string {
  return SUBJECTS.find((item) => item.id === id)?.name || id
}

export function studentName(student: {
  last_name: string
  first_name: string
  middle_name?: string | null
}): string {
  return [student.last_name, student.first_name, student.middle_name].filter(Boolean).join(' ')
}

export function splitFullName(fullName: string): {
  last_name: string
  first_name: string
  middle_name: string
} {
  const parts = fullName.trim().split(/\s+/).filter(Boolean)
  return {
    last_name: parts[0] || '',
    first_name: parts[1] || '',
    middle_name: parts.slice(2).join(' '),
  }
}
