import { defineStore } from 'pinia'
import { ref } from 'vue'
import api, { apiErrorMessage } from '../api/client'
import type { ClassJoinRequest, JoinClassResult, SchoolClass, Student, SubjectId } from '../types'
import { splitFullName, studentName } from '../utils/subjects'

function normalizeClass(item: Omit<SchoolClass, 'number' | 'letter'>): SchoolClass {
  const match = item.name.match(/^(\d+)(.*)$/)
  return { ...item, number: match?.[1] || item.name, letter: match?.[2]?.trim() || '' }
}

function normalizeStudent(item: Omit<Student, 'fullName'>): Student {
  return { ...item, fullName: studentName(item) }
}

export const useClassesStore = defineStore('classes', () => {
  const classes = ref<SchoolClass[]>([])
  const studentsByClass = ref<Record<string, Student[]>>({})
  const joinRequests = ref<ClassJoinRequest[]>([])
  const loaded = ref(false)

  const students = ref<Student[]>([])

  function rememberStudents(classId: string, list: Student[]) {
    studentsByClass.value[classId] = list
    const rest = students.value.filter((item) => item.school_class !== classId)
    students.value = [...rest, ...list]
  }

  async function fetchClasses() {
    const { data } = await api.get<Omit<SchoolClass, 'number' | 'letter'>[]>('/classes/')
    classes.value = data.map(normalizeClass)
    loaded.value = true
  }

  async function fetchMyClasses() {
    const { data } = await api.get<Omit<SchoolClass, 'number' | 'letter'>[]>('/classes/mine/')
    classes.value = data.map(normalizeClass)
    loaded.value = true
  }

  async function addClass(payload: { name: string; subject: SubjectId }) {
    const { data } = await api.post<Omit<SchoolClass, 'number' | 'letter'>>('/classes/', payload)
    const item = normalizeClass(data)
    classes.value.unshift(item)
    return item
  }

  async function updateClass(id: string, payload: { name: string; subject: SubjectId }) {
    const { data } = await api.patch<Omit<SchoolClass, 'number' | 'letter'>>(`/classes/${id}/`, payload)
    const index = classes.value.findIndex((item) => item.id === id)
    if (index !== -1) classes.value[index] = normalizeClass(data)
  }

  async function deleteClass(id: string) {
    await api.delete(`/classes/${id}/`)
    classes.value = classes.value.filter((item) => item.id !== id)
    delete studentsByClass.value[id]
  }

  function getClassById(id: string) {
    return classes.value.find((item) => item.id === id)
  }

  async function fetchStudents(classId: string) {
    const { data } = await api.get<Omit<Student, 'fullName'>[]>(`/classes/${classId}/students/`)
    const normalized = data.map(normalizeStudent)
    rememberStudents(classId, normalized)
    return normalized
  }

  function getStudentsByClass(classId: string): Student[] {
    return [...(studentsByClass.value[classId] || [])].sort((a, b) =>
      studentName(a).localeCompare(studentName(b), 'ru'),
    )
  }

  async function addStudent(classId: string, fullName: string) {
    const names = splitFullName(fullName)
    if (!names.last_name || !names.first_name) {
      throw new Error('Укажите фамилию и имя')
    }
    const { data } = await api.post<Omit<Student, 'fullName'>>(`/classes/${classId}/students/`, names)
    const student = normalizeStudent(data)
    const current = studentsByClass.value[classId] || []
    rememberStudents(classId, [...current, student])
    const schoolClass = getClassById(classId)
    if (schoolClass && schoolClass.students_count !== undefined) {
      schoolClass.students_count += 1
    }
    return student
  }

  async function addStudentsBatch(classId: string, rawText: string) {
    const lines = rawText
      .split('\n')
      .map((line) => line.trim().replace(/^\d+[\.)\s]+/, ''))
      .filter((line) => line.length > 0)
    let count = 0
    for (const line of lines) {
      await addStudent(classId, line)
      count += 1
    }
    return count
  }

  async function removeStudent(studentId: string) {
    await api.delete(`/students/${studentId}/`)
    for (const classId of Object.keys(studentsByClass.value)) {
      const list = studentsByClass.value[classId] || []
      if (list.some((item) => item.id === studentId)) {
        rememberStudents(
          classId,
          list.filter((item) => item.id !== studentId),
        )
      }
    }
  }

  async function joinByCode(code: string) {
    try {
      const { data } = await api.post<JoinClassResult>('/classes/join/', { code: code.trim() })
      await fetchMyClasses()
      return data
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Не удалось вступить в класс'))
    }
  }

  async function fetchJoinRequests() {
    const { data } = await api.get<ClassJoinRequest[]>('/join-requests/', {
      params: { status: 'pending' },
    })
    joinRequests.value = data
  }

  async function approveJoinRequest(id: string) {
    await api.post(`/join-requests/${id}/approve/`)
    joinRequests.value = joinRequests.value.filter((item) => item.id !== id)
  }

  async function rejectJoinRequest(id: string) {
    await api.post(`/join-requests/${id}/reject/`)
    joinRequests.value = joinRequests.value.filter((item) => item.id !== id)
  }

  return {
    classes,
    students,
    studentsByClass,
    joinRequests,
    loaded,
    fetchClasses,
    fetchMyClasses,
    addClass,
    updateClass,
    deleteClass,
    getClassById,
    fetchStudents,
    getStudentsByClass,
    addStudent,
    addStudentsBatch,
    removeStudent,
    joinByCode,
    fetchJoinRequests,
    approveJoinRequest,
    rejectJoinRequest,
  }
})
