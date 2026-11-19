import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api, { apiErrorMessage } from '../api/client'
import type { Exam, ExamStatus, ExamTemplate, SubjectId, TaskSpec } from '../types'
import { useAuthStore } from './auth'
import { subjectId } from '../utils/subjects'

function normalizeExam(item: Omit<Exam, 'classId' | 'className' | 'academicYear' | 'passingScoreSecondary' | 'maxPrimaryScore' | 'createdAt'>): Exam {
  return {
    ...item,
    tasks: item.tasks.map((task) => ({ ...task, taskNumber: task.number, maxScore: task.max_score })),
    classId: item.school_class,
    className: item.school_class_name,
    academicYear: item.academic_year,
    passingScoreSecondary: item.passing_score_secondary,
    maxPrimaryScore: item.max_primary_score,
    createdAt: item.created_at,
  }
}

export const useMockTestsStore = defineStore('mockTests', () => {
  const exams = ref<Exam[]>([])
  const templates = ref<ExamTemplate[]>([])
  const loaded = ref(false)

  const mockTests = computed(() => exams.value)

  async function fetchExams(classId?: string) {
    const auth = useAuthStore()
    const path = auth.isStudent ? '/exams/mine/' : '/exams/'
    const { data } = await api.get<Omit<Exam, 'classId' | 'className' | 'academicYear' | 'passingScoreSecondary' | 'maxPrimaryScore' | 'createdAt'>[]>(path, {
      params: classId ? { class_id: classId } : undefined,
    })
    exams.value = data.map(normalizeExam)
    loaded.value = true
    return data
  }

  async function fetchTemplates(subject?: SubjectId) {
    const { data } = await api.get<ExamTemplate[]>('/exam-templates/', {
      params: subject ? { subject } : undefined,
    })
    templates.value = data
    return data
  }

  async function addMockTest(payload: {
    title: string
    date: string
    classId: string
    subject: SubjectId
    academicYear?: string
    tasks?: TaskSpec[]
    passingScoreSecondary?: number
    templateId?: string | null
  }): Promise<Exam> {
    try {
      const body: Record<string, unknown> = {
        title: payload.title.trim(),
        date: payload.date,
        school_class: payload.classId,
        subject: subjectId(payload.subject),
        academic_year: payload.academicYear,
        passing_score_secondary: payload.passingScoreSecondary,
      }
      if (payload.templateId) {
        body.template = payload.templateId
      }
      if (!payload.templateId && payload.tasks && payload.tasks.length > 0) {
        body.tasks = payload.tasks.map((task) => ({
          number: task.taskNumber,
          max_score: task.maxScore,
        }))
        body.use_proportional_conversion = !payload.templateId
      }
      const { data } = await api.post<Parameters<typeof normalizeExam>[0]>('/exams/', body)
      const exam = normalizeExam(data)
      exams.value.unshift(exam)
      return exam
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Не удалось создать пробник'))
    }
  }

  async function updateMockTest(
    id: string,
    payload: {
      title?: string
      date?: string
      academicYear?: string
      passingScoreSecondary?: number
    },
  ) {
    try {
      const { data } = await api.patch<Parameters<typeof normalizeExam>[0]>(`/exams/${id}/`, {
        title: payload.title,
        date: payload.date,
        academic_year: payload.academicYear,
        passing_score_secondary: payload.passingScoreSecondary,
      })
      const index = exams.value.findIndex((item) => item.id === id)
      const exam = normalizeExam(data)
      if (index !== -1) exams.value[index] = exam
      return exam
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Не удалось обновить пробник'))
    }
  }

  async function deleteMockTest(id: string) {
    try {
      await api.delete(`/exams/${id}/`)
      exams.value = exams.value.filter((item) => item.id !== id)
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Не удалось удалить пробник'))
    }
  }

  async function publishExam(id: string) {
    try {
      const { data } = await api.post<{ id: string; status: ExamStatus }>(`/exams/${id}/publish/`)
      const exam = exams.value.find((item) => item.id === id)
      if (exam) exam.status = data.status
      return data
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Не удалось опубликовать пробник'))
    }
  }

  async function completeExam(id: string) {
    try {
      const { data } = await api.post<{ id: string; status: ExamStatus }>(`/exams/${id}/complete/`)
      const exam = exams.value.find((item) => item.id === id)
      if (exam) exam.status = data.status
      return data
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Не удалось завершить пробник'))
    }
  }

  function getMockTestById(id: string) {
    return exams.value.find((item) => item.id === id)
  }

  function getTestsByClass(classId: string) {
    return exams.value
      .filter((item) => item.classId === classId)
      .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
  }

  return {
    exams,
    mockTests,
    templates,
    loaded,
    fetchExams,
    fetchTemplates,
    addMockTest,
    updateMockTest,
    deleteMockTest,
    publishExam,
    completeExam,
    getMockTestById,
    getTestsByClass,
  }
})
