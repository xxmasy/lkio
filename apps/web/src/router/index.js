import { createRouter, createWebHistory } from 'vue-router';
import OverviewView from '@/views/OverviewView.vue';
import ProjectsView from '@/views/ProjectsView.vue';
import ProjectDetailView from '@/views/ProjectDetailView.vue';
import GraphView from '@/views/GraphView.vue';
const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/',
            redirect: '/overview'
        },
        {
            path: '/overview',
            name: 'overview',
            component: OverviewView,
            meta: { title: '概览 (Overview)' }
        },
        {
            path: '/projects',
            name: 'projects',
            component: ProjectsView,
            meta: { title: '纳管项目 (Projects)' }
        },
        {
            path: '/projects/:id',
            name: 'project-detail',
            component: ProjectDetailView,
            meta: { title: '项目详情' }
        },
        {
            path: '/graph',
            name: 'graph',
            component: GraphView,
            meta: { title: '知识拓扑 (Graph)' }
        }
    ]
});
router.beforeEach((to, from, next) => {
    if (to.meta.title) {
        document.title = `${to.meta.title} - LKIO`;
    }
    next();
});
export default router;
