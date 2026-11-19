import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api, { apiErrorMessage } from '../api/client'
import type {
  ClassAnalyticsSummary,
  ClassDynamicsItem,
  StudentHistoryItem,
  StudentResult,
  MockTestResultSheet,
} from '../types'

export const useResultsStore = defineStore('results', () => {
  const resultsByExam = ref<Record<string, StudentResult[]>>({})
  const myResultByExam = ref<Record<string, StudentResult>>({})
  const analyticsByExam = ref<Record<string, ClassAnalyticsSummary>>({})
  const dynamicsByClass = ref<Record<string, ClassDynamicsItem[]>>({})
  const historyByStudent = ref<Record<string, StudentHistoryItem[]>>({})

  function normalizeAnalytics(data: ClassAnalyticsSummary): ClassAnalyticsSummary {
    return {
      ...data,
      totalStudents: data.total_students,
      attendedStudents: data.attended_students,
      avgPrimary: data.avg_primary,
      avgSecondary: data.avg_secondary,
      maxSecondary: data.max_secondary,
      minSecondary: data.min_secondary,
      passingThreshold: data.passing_threshold,
      passedCount: data.passed_count,
      passedPercent: data.passed_percent,
      highAchieversCount: data.high_achievers_count,
      highAchieversPercent: data.high_achievers_percent,
      scoreDistribution: data.score_distribution,
      taskSolvability: data.task_solvability.map((item) => ({
        taskNumber: item.task_number,
        maxScore: item.max_score,
        avgScore: item.avg_score,
        percent: item.percent,
      })),
    }
  }
  const resultSheets = computed<MockTestResultSheet[]>(() =>
    Object.entries(resultsByExam.value).map(([examId, results]) => ({
      id: `sheet-${examId}`,
      mockTestId: examId,
      updatedAt: new Date().toISOString(),
      studentScores: Object.fromEntries(results.map((result) => [result.student_id, {
        studentId: result.student_id,
        scores: result.scores_by_number,
        primaryScore: result.summary.primary_score,
        secondaryScore: result.summary.secondary_score || 0,
      }])),
    })),
  )

  async function fetchResults(examId: string) {
    await api.post(`/exams/${examId}/sync-students/`)
    const { data } = await api.get<StudentResult[]>(`/exams/${examId}/results/`)
    resultsByExam.value[examId] = data
    return data
  }

  function getSheetByMockTestId(examId: string): MockTestResultSheet {
    return resultSheets.value.find((sheet) => sheet.mockTestId === examId) || {
      id: `sheet-${examId}`,
      mockTestId: examId,
      updatedAt: new Date().toISOString(),
      studentScores: {},
    }
  }

  async function saveSheet(sheet: MockTestResultSheet) {
    for (const result of Object.values(sheet.studentScores)) {
      const current = (resultsByExam.value[sheet.mockTestId] || []).find((item) => item.student_id === result.studentId)
      if (current) await saveTeacherScores(current.id, sheet.mockTestId, result.scores)
    }
  }

  async function fetchMyResult(examId: string) {
    const { data } = await api.get<StudentResult>(`/exams/mine/${examId}/`)
    myResultByExam.value[examId] = data
    return data
  }

  async function saveTeacherScores(resultId: string, examId: string, scores: Record<number, number | null>) {
    try {
      const { data } = await api.patch<StudentResult>(`/results/${resultId}/scores/`, {
        scores: Object.entries(scores).map(([taskNumber, score]) => ({
          task_number: Number(taskNumber),
          score,
        })),
      })
      const list = resultsByExam.value[examId] || []
      const index = list.findIndex((item) => item.id === resultId)
      if (index !== -1) list[index] = data
      else resultsByExam.value[examId] = [...list, data]
      return data
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Не удалось сохранить баллы'))
    }
  }

  async function saveMyScores(examId: string, scores: Record<number, number>) {
    try {
      const { data } = await api.patch<StudentResult>(`/exams/mine/${examId}/scores/`, {
        scores: Object.entries(scores).map(([taskNumber, score]) => ({
          task_number: Number(taskNumber),
          score,
        })),
      })
      myResultByExam.value[examId] = data
      return data
    } catch (error) {
      throw new Error(apiErrorMessage(error, 'Не удалось сохранить баллы'))
    }
  }

  async function fetchAnalytics(examId: string, threshold?: number) {
    const { data } = await api.get<ClassAnalyticsSummary>(`/exams/${examId}/analytics/`, {
      params: threshold !== undefined ? { threshold } : undefined,
    })
    const normalized = normalizeAnalytics(data)
    analyticsByExam.value[examId] = normalized
    return normalized
  }

  async function fetchDynamics(classId: string) {
    const { data } = await api.get<ClassDynamicsItem[]>(`/classes/${classId}/dynamics/`)
    dynamicsByClass.value[classId] = data
    return data
  }

  async function fetchStudentHistory(studentId: string) {
    const { data } = await api.get<StudentHistoryItem[]>(`/students/${studentId}/history/`)
    const normalized = data.map((item) => ({
      ...item,
      testId: item.test_id,
      primaryScore: item.primary_score,
      secondaryScore: item.secondary_score || 0,
      maxPrimaryScore: item.max_primary_score,
    }))
    historyByStudent.value[studentId] = normalized
    return normalized
  }

  function getClassAnalytics(_classId: string, examId?: string, _threshold?: number) {
    return analyticsByExam.value[examId || _classId] || null
  }

  function getStudentHistory(studentId: string) {
    return historyByStudent.value[studentId] || []
  }

  return {
    resultsByExam,
    resultSheets,
    myResultByExam,
    analyticsByExam,
    dynamicsByClass,
    historyByStudent,
    fetchResults,
    getSheetByMockTestId,
    saveSheet,
    fetchMyResult,
    saveTeacherScores,
    saveMyScores,
    fetchAnalytics,
    fetchDynamics,
    fetchStudentHistory,
    getClassAnalytics,
    getStudentHistory,
  }
})
