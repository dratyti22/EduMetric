<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import Navbar from './components/Navbar.vue';
import { useAuthStore } from './stores/auth';
import { useClassesStore } from './stores/classes';
import { useMockTestsStore } from './stores/mockTests';

const route = useRoute();
const showNavbar = computed(() => route.path !== '/login');
const authStore = useAuthStore();
const classesStore = useClassesStore();
const mockTestsStore = useMockTestsStore();

onMounted(async () => {
  if (!authStore.token) return;
  await authStore.restoreSession();
  if (!authStore.isAuthenticated) return;
  if (authStore.isTeacher) await classesStore.fetchClasses();
  else await classesStore.fetchMyClasses();
  await mockTestsStore.fetchExams();
});
</script>

<template>
  <div class="app-container">
    <Navbar v-if="showNavbar" />
    <main :class="{ 'main-content': showNavbar }">
      <router-view />
    </main>
  </div>
</template>

<style>
@import './assets/main.css';
</style>
