<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useClassesStore } from '../stores/classes';
import { SUBJECTS, studentName, subjectName } from '../utils/subjects';
import type { SchoolClass, Student, SubjectId } from '../types';
import Modal from '../components/Modal.vue';
import {
  Users,
  Plus,
  Edit2,
  Trash2,
  UserPlus,
  ClipboardList,
  AlertTriangle,
  Search,
  Copy,
  Check,
} from 'lucide-vue-next';

const classesStore = useClassesStore();
const authStore = useAuthStore();
const pageError = ref('');
const joinCode = ref('');
const joinMessage = ref('');
const copiedCode = ref('');

// Поиск / фильтр
const searchQuery = ref('');

// Модальное окно создания / редактирования класса
const isClassModalOpen = ref(false);
const isEditing = ref(false);
const editingClassId = ref<string | null>(null);

const classForm = ref<{
  name: string;
  subject: SubjectId;
}>({
  name: '11А',
  subject: 'math_profile',
});

// Модальное окно управления учениками
const isRosterModalOpen = ref(false);
const activeClass = ref<SchoolClass | null>(null);
const singleStudentName = ref('');
const batchStudentsText = ref('');
const showBatchInput = ref(false);

// Модальное окно подтверждения удаления
const isDeleteModalOpen = ref(false);
const classToDelete = ref<SchoolClass | null>(null);

function openCreateModal() {
  isEditing.value = false;
  editingClassId.value = null;
  classForm.value = { name: '11А', subject: 'math_profile' };
  isClassModalOpen.value = true;
}

function openEditModal(cls: SchoolClass) {
  isEditing.value = true;
  editingClassId.value = cls.id;
  classForm.value = { name: cls.name, subject: cls.subject };
  isClassModalOpen.value = true;
}

async function saveClass() {
  const name = classForm.value.name.trim();
  if (!name) {
    alert('Укажите название класса');
    return;
  }
  try {
    if (isEditing.value && editingClassId.value) {
      await classesStore.updateClass(editingClassId.value, {
        name,
        subject: classForm.value.subject,
      });
    } else {
      await classesStore.addClass({ name, subject: classForm.value.subject });
    }
    isClassModalOpen.value = false;
  } catch (err: any) {
    alert(err.message || 'Не удалось сохранить класс');
  }
}

function confirmDeleteClass(cls: SchoolClass) {
  classToDelete.value = cls;
  isDeleteModalOpen.value = true;
}

async function executeDeleteClass() {
  if (!classToDelete.value) return;
  await classesStore.deleteClass(classToDelete.value.id);
  classToDelete.value = null;
  isDeleteModalOpen.value = false;
}

// Управление учениками
async function openRosterModal(cls: SchoolClass) {
  activeClass.value = cls;
  singleStudentName.value = '';
  batchStudentsText.value = '';
  showBatchInput.value = false;
  isRosterModalOpen.value = true;
  await classesStore.fetchStudents(cls.id);
}

async function handleAddSingleStudent() {
  if (!activeClass.value || !singleStudentName.value.trim()) return;
  try {
    await classesStore.addStudent(activeClass.value.id, singleStudentName.value);
    singleStudentName.value = '';
  } catch (err: any) {
    alert(err.message);
  }
}

async function handleBatchAddStudents() {
  if (!activeClass.value || !batchStudentsText.value.trim()) return;
  try {
    const count = await classesStore.addStudentsBatch(activeClass.value.id, batchStudentsText.value);
    batchStudentsText.value = '';
    showBatchInput.value = false;
    alert(`Добавлено учеников: ${count}`);
  } catch (err: any) {
    alert(err.message);
  }
}

async function handleRemoveStudent(studentId: string) {
  if (confirm('Удалить ученика из класса?')) {
    await classesStore.removeStudent(studentId);
  }
}

function getStudents(classId: string): Student[] {
  return classesStore.getStudentsByClass(classId);
}

const filteredClasses = computed(() => {
  const query = searchQuery.value.toLowerCase().trim();
  if (!query) return classesStore.classes;
  return classesStore.classes.filter(
    (item) =>
      item.name.toLowerCase().includes(query) ||
      subjectName(item.subject).toLowerCase().includes(query) ||
      (item.join_code || '').toLowerCase().includes(query),
  );
});

async function copyCode(code: string) {
  await navigator.clipboard.writeText(code);
  copiedCode.value = code;
  setTimeout(() => {
    copiedCode.value = '';
  }, 1500);
}

async function handleJoin() {
  joinMessage.value = '';
  pageError.value = '';
  try {
    const result = await classesStore.joinByCode(joinCode.value);
    joinCode.value = '';
    if (result.status === 'pending') {
      joinMessage.value = 'ФИО совпало с карточкой класса. Ждём подтверждения учителя.';
    } else if (result.status === 'already_member') {
      joinMessage.value = 'Вы уже состоите в этом классе.';
    } else {
      joinMessage.value = `Вы вступили в класс «${result.school_class.name}».`;
    }
  } catch (err: any) {
    pageError.value = err.message;
  }
}

async function approveRequest(id: string) {
  await classesStore.approveJoinRequest(id);
  if (activeClass.value) await classesStore.fetchStudents(activeClass.value.id);
  await classesStore.fetchClasses();
}

onMounted(async () => {
  if (authStore.isTeacher) {
    await classesStore.fetchClasses();
    await classesStore.fetchJoinRequests();
  } else {
    await classesStore.fetchMyClasses();
  }
});
</script>

<template>
  <div class="classes-view">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ authStore.isTeacher ? 'Управление классами' : 'Мои классы' }}</h1>
        <p class="page-subtitle">
          {{ authStore.isTeacher ? 'Создайте класс и передайте ученикам код вступления' : 'Вступите в класс по коду от учителя' }}
        </p>
      </div>
      <button v-if="authStore.isTeacher" class="btn btn-primary" @click="openCreateModal">
        <Plus :size="18" />
        <span>Создать класс</span>
      </button>
    </div>

    <div v-if="!authStore.isTeacher" class="card" style="margin-bottom: 1rem;">
      <form class="form-row" style="align-items: flex-end;" @submit.prevent="handleJoin">
        <div class="form-group" style="flex: 1; margin-bottom: 0;">
          <label class="form-label">Код класса</label>
          <input v-model="joinCode" class="form-input" placeholder="EX-7K4p9M2A" required />
        </div>
        <button class="btn btn-primary" type="submit">Вступить</button>
      </form>
      <p v-if="joinMessage" style="margin-top: 0.75rem;">{{ joinMessage }}</p>
      <p v-if="pageError" class="text-danger" style="margin-top: 0.75rem;">{{ pageError }}</p>
    </div>

    <div v-if="authStore.isTeacher && classesStore.joinRequests.length" class="card" style="margin-bottom: 1rem;">
      <h3>Запросы на привязку</h3>
      <div v-for="request in classesStore.joinRequests" :key="request.id" class="form-row" style="align-items: center; margin-top: 0.75rem;">
        <div style="flex: 1;">
          <strong>{{ request.user_name }}</strong> хочет привязаться к карточке
          «{{ request.matched_student_name }}» в классе {{ request.class_name }}
        </div>
        <button class="btn btn-primary btn-sm" @click="approveRequest(request.id)">Подтвердить</button>
        <button class="btn btn-secondary btn-sm" @click="classesStore.rejectJoinRequest(request.id)">Отклонить</button>
      </div>
    </div>

    <!-- Панель поиска и сводка -->
    <div class="toolbar card">
      <div class="search-input-box">
        <Search :size="18" class="search-icon" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Поиск по номеру, букве или предмету..."
          class="form-input search-field"
        />
      </div>
      <div class="toolbar-stats">
        <span>Всего классов: <strong>{{ classesStore.classes.length }}</strong></span>
      </div>
    </div>

    <!-- Сетка классов -->
    <div v-if="filteredClasses.length === 0" class="empty-placeholder card">
      <Users :size="48" class="empty-icon" />
      <h3>Классы не найдены</h3>
      <p>Создайте новый класс или измените параметры поиска</p>
      <button class="btn btn-primary btn-sm" @click="openCreateModal" style="margin-top: 1rem;">
        <Plus :size="16" /> Создать класс
      </button>
    </div>

    <div v-else class="grid-cards">
      <div v-for="cls in filteredClasses" :key="cls.id" class="card card-hover class-card">
        <div class="class-card-top">
          <div class="class-badge-num">{{ cls.name }}</div>
          <span class="badge badge-primary">{{ subjectName(cls.subject) }}</span>
        </div>

        <p v-if="authStore.isTeacher && cls.join_code" class="class-desc">
          Код: <strong>{{ cls.join_code }}</strong>
          <button class="btn btn-secondary btn-icon btn-sm" type="button" @click="copyCode(cls.join_code)">
            <Check v-if="copiedCode === cls.join_code" :size="14" />
            <Copy v-else :size="14" />
          </button>
        </p>

        <div class="class-stats-box">
          <div class="students-count-badge">
            <Users :size="16" />
            <span><strong>{{ cls.students_count ?? getStudents(cls.id).length }}</strong> учеников</span>
          </div>
        </div>

        <div class="class-card-actions">
          <button v-if="authStore.isTeacher" class="btn btn-secondary btn-sm" @click="openRosterModal(cls)">
            <UserPlus :size="16" />
            <span>Ученики</span>
          </button>
          <div v-if="authStore.isTeacher" class="actions-group-right">
            <button class="btn btn-secondary btn-icon" @click="openEditModal(cls)" title="Редактировать класс">
              <Edit2 :size="16" />
            </button>
            <button class="btn btn-danger btn-icon" @click="confirmDeleteClass(cls)" title="Удалить класс">
              <Trash2 :size="16" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Модальное окно Создания / Редактирования Класса -->
    <Modal
      :isOpen="isClassModalOpen"
      :title="isEditing ? 'Редактировать информацию о классе' : 'Создать новый класс'"
      @close="isClassModalOpen = false"
    >
      <form @submit.prevent="saveClass">
        <div class="form-group">
          <label class="form-label">Название класса</label>
          <input v-model="classForm.name" class="form-input" placeholder="11А" required />
        </div>
        <div class="form-group">
          <label class="form-label">Предмет</label>
          <select v-model="classForm.subject" class="form-select">
            <option v-for="item in SUBJECTS" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </div>
      </form>

      <template #footer>
        <button class="btn btn-secondary" @click="isClassModalOpen = false">Отмена</button>
        <button class="btn btn-primary" @click="saveClass">
          {{ isEditing ? 'Сохранить изменения' : 'Создать класс' }}
        </button>
      </template>
    </Modal>

    <!-- Модальное окно управления учениками -->
    <Modal
      :isOpen="isRosterModalOpen"
      :title="activeClass ? `Список учеников: ${activeClass.name}` : 'Список учеников'"
      maxWidth="680px"
      @close="isRosterModalOpen = false"
    >
      <div v-if="activeClass" class="roster-container">
        <!-- Блок добавления одиночного ученика -->
        <div class="add-student-box">
          <div class="form-row" style="align-items: flex-end;">
            <div class="form-group" style="flex: 1; margin-bottom: 0;">
              <label class="form-label">Добавить ученика (ФИО)</label>
              <input
                v-model="singleStudentName"
                type="text"
                class="form-input"
                placeholder="Иванов Иван Иванович"
                @keyup.enter="handleAddSingleStudent"
              />
            </div>
            <button class="btn btn-primary" @click="handleAddSingleStudent">
              <Plus :size="16" /> Добавить
            </button>
          </div>

          <div style="margin-top: 0.65rem;">
            <button
              class="btn-text-link"
              type="button"
              @click="showBatchInput = !showBatchInput"
            >
              <ClipboardList :size="14" />
              <span>{{ showBatchInput ? 'Скрыть массовый ввод' : 'Добавить списком (из журнала или Excel)' }}</span>
            </button>
          </div>
        </div>

        <!-- Массовое добавление списком -->
        <div v-if="showBatchInput" class="batch-import-box">
          <label class="form-label">Вставьте список ФИО (каждый ученик с новой строки):</label>
          <textarea
            v-model="batchStudentsText"
            class="form-textarea"
            rows="5"
            placeholder="Иванов Иван Иванович&#10;Петров Петр Сергеевич&#10;Сидорова Анна Николаевна"
          ></textarea>
          <div style="margin-top: 0.5rem; display: flex; justify-content: flex-end; gap: 0.5rem;">
            <button class="btn btn-secondary btn-sm" @click="showBatchInput = false">Свернуть</button>
            <button class="btn btn-primary btn-sm" @click="handleBatchAddStudents">Импортировать список</button>
          </div>
        </div>

        <!-- Таблица учеников -->
        <div class="roster-table-wrapper">
          <div class="roster-header-row">
            <span class="roster-count">Всего учеников: <strong>{{ getStudents(activeClass.id).length }}</strong></span>
          </div>

          <div v-if="getStudents(activeClass.id).length === 0" class="empty-roster">
            В этом классе пока нет учеников. Добавьте первого ученика или вставьте список выше.
          </div>

          <div v-else class="table-container" style="max-height: 320px; overflow-y: auto;">
            <table class="table">
              <thead>
                <tr>
                  <th style="width: 45px;">№</th>
                  <th>ФИО Ученика</th>
                  <th style="width: 70px; text-align: right;">Действие</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(student, idx) in getStudents(activeClass.id)" :key="student.id">
                  <td>{{ idx + 1 }}</td>
                  <td style="font-weight: 500;">
                    {{ studentName(student) }}
                    <span v-if="student.is_linked" class="badge badge-primary">аккаунт</span>
                  </td>
                  <td style="text-align: right;">
                    <button
                      class="btn btn-danger btn-icon btn-sm"
                      @click="handleRemoveStudent(student.id)"
                      title="Удалить ученика"
                    >
                      <Trash2 :size="14" />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <template #footer>
        <button class="btn btn-primary" @click="isRosterModalOpen = false">Готово</button>
      </template>
    </Modal>

    <!-- Модальное окно подтверждения удаления класса -->
    <Modal
      :isOpen="isDeleteModalOpen"
      title="Удаление класса"
      maxWidth="460px"
      @close="isDeleteModalOpen = false"
    >
      <div v-if="classToDelete" class="delete-confirmation">
        <div class="delete-icon-box">
          <AlertTriangle :size="32" />
        </div>
        <p class="delete-msg">
          Вы уверены, что хотите удалить класс
          <strong>{{ classToDelete.number }} «{{ classToDelete.letter }}»</strong>?
        </p>
        <p class="delete-sub">
          Все привязанные ученики ({{ getStudents(classToDelete.id).length }} чел.) также будут удалены из системы.
        </p>
      </div>

      <template #footer>
        <button class="btn btn-secondary" @click="isDeleteModalOpen = false">Отмена</button>
        <button class="btn btn-danger" @click="executeDeleteClass">Да, удалить класс</button>
      </template>
    </Modal>
  </div>
</template>

<style scoped>
.classes-view {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 1.25rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.search-input-box {
  position: relative;
  flex: 1;
  max-width: 400px;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  top: 50%;
  transform: translateY(-50%);
  color: var(--gray-400);
}

.search-field {
  padding-left: 2.35rem;
}

.toolbar-stats {
  font-size: 0.875rem;
  color: var(--gray-600);
}

.class-card {
  display: flex;
  flex-direction: column;
}

.class-card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.class-badge-num {
  font-size: 1.35rem;
  font-weight: 800;
  color: var(--gray-900);
  line-height: 1.2;
}

.class-desc {
  font-size: 0.875rem;
  color: var(--gray-600);
  min-height: 40px;
  line-height: 1.4;
  margin-bottom: 1rem;
}

.text-muted {
  color: var(--gray-400);
  font-style: italic;
}

.class-stats-box {
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-md);
  padding: 0.75rem;
  margin-bottom: 1.25rem;
}

.students-count-badge {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--gray-700);
}

.class-card-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: auto;
  padding-top: 0.75rem;
  border-top: 1px solid var(--gray-100);
}

.actions-group-right {
  display: flex;
  gap: 0.4rem;
}

.empty-placeholder {
  text-align: center;
  padding: 3rem 1.5rem;
  color: var(--gray-500);
}

.empty-icon {
  color: var(--gray-300);
  margin-bottom: 0.75rem;
}

/* Roster Modal */
.roster-container {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.add-student-box {
  background: var(--gray-50);
  border: 1px solid var(--gray-200);
  padding: 1rem;
  border-radius: var(--radius-md);
}

.btn-text-link {
  background: none;
  border: none;
  color: var(--primary);
  font-size: 0.825rem;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0;
}

.btn-text-link:hover {
  text-decoration: underline;
}

.batch-import-box {
  background: white;
  border: 1px solid var(--gray-300);
  border-radius: var(--radius-md);
  padding: 1rem;
  box-shadow: var(--shadow-sm);
}

.roster-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.roster-count {
  font-size: 0.85rem;
  color: var(--gray-600);
}

.empty-roster {
  text-align: center;
  padding: 1.75rem;
  background: var(--gray-50);
  border: 1px dashed var(--gray-300);
  border-radius: var(--radius-md);
  color: var(--gray-500);
  font-size: 0.875rem;
}

/* Delete confirmation */
.delete-confirmation {
  text-align: center;
  padding: 0.5rem 0;
}

.delete-icon-box {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-full);
  background: var(--danger-bg);
  color: var(--danger);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
}

.delete-msg {
  font-size: 1rem;
  color: var(--gray-900);
  margin-bottom: 0.5rem;
}

.delete-sub {
  font-size: 0.85rem;
  color: var(--gray-500);
}
</style>
