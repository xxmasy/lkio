import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { ArrowLeft, Connection, Refresh } from '@element-plus/icons-vue';
import { api, } from '@/api/client';
import { ElMessage } from 'element-plus';
const route = useRoute();
const loading = ref(true);
const scanning = ref(false);
const activeTab = ref('dependencies');
const depSearch = ref('');
const project = ref(null);
const snapshot = ref(null);
const scanRuns = ref([]);
const dependencies = ref([]);
const filteredDependencies = computed(() => {
    if (!depSearch.value.trim())
        return dependencies.value;
    const q = depSearch.value.toLowerCase().trim();
    return dependencies.value.filter((d) => d.name.toLowerCase().includes(q) ||
        d.ecosystem.toLowerCase().includes(q) ||
        d.scope.toLowerCase().includes(q) ||
        d.manifest_path.toLowerCase().includes(q));
});
const getLanguageColor = (lang) => {
    const map = {
        Vue: '#41b883',
        TypeScript: '#3178c6',
        JavaScript: '#f7df1e',
        Java: '#b07219',
        HTML: '#e34c26',
        CSS: '#563d7c',
        SCSS: '#c6538c',
        Python: '#3572a5',
    };
    return map[lang] || '#409eff';
};
const formatDate = (isoStr) => {
    if (!isoStr)
        return '';
    const d = new Date(isoStr);
    return d.toLocaleString('zh-CN', { hour12: false });
};
const loadProjectData = async (idOrKey) => {
    try {
        project.value = await api.getProject(idOrKey);
        const [snapData, runsData, depsData] = await Promise.all([
            api.getSnapshot(idOrKey),
            api.getScanRuns(idOrKey, 20),
            api.getDependencies(idOrKey),
        ]);
        snapshot.value = snapData;
        scanRuns.value = runsData;
        dependencies.value = depsData;
    }
    catch (err) {
        ElMessage.error(`加载项目数据失败: ${err.message}`);
    }
};
const handleTriggerScan = async () => {
    if (!project.value)
        return;
    scanning.value = true;
    try {
        ElMessage.info(`正在触发 ${project.value.key} 只读代码摄取扫描...`);
        await api.triggerScan(project.value.key);
        ElMessage.success('摄取扫描完成！已同步知识图谱与最新快照');
        await loadProjectData(project.value.key);
    }
    catch (err) {
        ElMessage.error(`摄取扫描失败: ${err.message}`);
    }
    finally {
        scanning.value = false;
    }
};
onMounted(async () => {
    const id = route.params.id;
    loading.value = true;
    await loadProjectData(id);
    loading.value = false;
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['metrics-block']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "project-detail-container" },
});
__VLS_asFunctionalDirective(__VLS_directives.vLoading)(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.loading) }, null, null);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "header-nav" },
});
const __VLS_0 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ 'onClick': {} },
    icon: (__VLS_ctx.ArrowLeft),
}));
const __VLS_2 = __VLS_1({
    ...{ 'onClick': {} },
    icon: (__VLS_ctx.ArrowLeft),
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_4;
let __VLS_5;
let __VLS_6;
const __VLS_7 = {
    onClick: (...[$event]) => {
        __VLS_ctx.$router.push('/projects');
    }
};
__VLS_3.slots.default;
var __VLS_3;
if (__VLS_ctx.project) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "header-actions" },
    });
    const __VLS_8 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
        ...{ 'onClick': {} },
        type: "warning",
        icon: (__VLS_ctx.Refresh),
        loading: (__VLS_ctx.scanning),
    }));
    const __VLS_10 = __VLS_9({
        ...{ 'onClick': {} },
        type: "warning",
        icon: (__VLS_ctx.Refresh),
        loading: (__VLS_ctx.scanning),
    }, ...__VLS_functionalComponentArgsRest(__VLS_9));
    let __VLS_12;
    let __VLS_13;
    let __VLS_14;
    const __VLS_15 = {
        onClick: (__VLS_ctx.handleTriggerScan)
    };
    __VLS_11.slots.default;
    var __VLS_11;
    const __VLS_16 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
        ...{ 'onClick': {} },
        type: "primary",
        icon: (__VLS_ctx.Connection),
    }));
    const __VLS_18 = __VLS_17({
        ...{ 'onClick': {} },
        type: "primary",
        icon: (__VLS_ctx.Connection),
    }, ...__VLS_functionalComponentArgsRest(__VLS_17));
    let __VLS_20;
    let __VLS_21;
    let __VLS_22;
    const __VLS_23 = {
        onClick: (...[$event]) => {
            if (!(__VLS_ctx.project))
                return;
            __VLS_ctx.$router.push(`/graph?project=${__VLS_ctx.project.key}`);
        }
    };
    __VLS_19.slots.default;
    var __VLS_19;
}
if (__VLS_ctx.project) {
    const __VLS_24 = {}.ElCard;
    /** @type {[typeof __VLS_components.ElCard, typeof __VLS_components.elCard, typeof __VLS_components.ElCard, typeof __VLS_components.elCard, ]} */ ;
    // @ts-ignore
    const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
        shadow: "hover",
        ...{ class: "detail-card" },
    }));
    const __VLS_26 = __VLS_25({
        shadow: "hover",
        ...{ class: "detail-card" },
    }, ...__VLS_functionalComponentArgsRest(__VLS_25));
    __VLS_27.slots.default;
    {
        const { header: __VLS_thisSlot } = __VLS_27.slots;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "card-header" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "title-area" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "project-name" },
        });
        (__VLS_ctx.project.name);
        const __VLS_28 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
            size: "default",
            effect: "dark",
        }));
        const __VLS_30 = __VLS_29({
            size: "default",
            effect: "dark",
        }, ...__VLS_functionalComponentArgsRest(__VLS_29));
        __VLS_31.slots.default;
        (__VLS_ctx.project.key);
        var __VLS_31;
        const __VLS_32 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
            type: (__VLS_ctx.project.kind === 'frontend' ? 'warning' : 'success'),
        }));
        const __VLS_34 = __VLS_33({
            type: (__VLS_ctx.project.kind === 'frontend' ? 'warning' : 'success'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_33));
        __VLS_35.slots.default;
        (__VLS_ctx.project.kind);
        var __VLS_35;
        const __VLS_36 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
            type: (__VLS_ctx.project.status === 'ACTIVE' ? 'success' : 'info'),
        }));
        const __VLS_38 = __VLS_37({
            type: (__VLS_ctx.project.status === 'ACTIVE' ? 'success' : 'info'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_37));
        __VLS_39.slots.default;
        (__VLS_ctx.project.status);
        var __VLS_39;
    }
    const __VLS_40 = {}.ElDescriptions;
    /** @type {[typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, ]} */ ;
    // @ts-ignore
    const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
        title: "基础项目元数据",
        column: (2),
        border: true,
    }));
    const __VLS_42 = __VLS_41({
        title: "基础项目元数据",
        column: (2),
        border: true,
    }, ...__VLS_functionalComponentArgsRest(__VLS_41));
    __VLS_43.slots.default;
    const __VLS_44 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
        label: "Project ID",
    }));
    const __VLS_46 = __VLS_45({
        label: "Project ID",
    }, ...__VLS_functionalComponentArgsRest(__VLS_45));
    __VLS_47.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({});
    (__VLS_ctx.project.id);
    var __VLS_47;
    const __VLS_48 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_49 = __VLS_asFunctionalComponent(__VLS_48, new __VLS_48({
        label: "架构角色 (Role)",
    }));
    const __VLS_50 = __VLS_49({
        label: "架构角色 (Role)",
    }, ...__VLS_functionalComponentArgsRest(__VLS_49));
    __VLS_51.slots.default;
    const __VLS_52 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
        type: "info",
        effect: "plain",
    }));
    const __VLS_54 = __VLS_53({
        type: "info",
        effect: "plain",
    }, ...__VLS_functionalComponentArgsRest(__VLS_53));
    __VLS_55.slots.default;
    (__VLS_ctx.project.role);
    var __VLS_55;
    var __VLS_51;
    const __VLS_56 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_57 = __VLS_asFunctionalComponent(__VLS_56, new __VLS_56({
        label: "本地工作区路径 (只读)",
        span: (2),
    }));
    const __VLS_58 = __VLS_57({
        label: "本地工作区路径 (只读)",
        span: (2),
    }, ...__VLS_functionalComponentArgsRest(__VLS_57));
    __VLS_59.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({
        ...{ class: "path-box" },
    });
    (__VLS_ctx.project.local_path);
    var __VLS_59;
    const __VLS_60 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
        label: "当前分支 / HEAD",
    }));
    const __VLS_62 = __VLS_61({
        label: "当前分支 / HEAD",
    }, ...__VLS_functionalComponentArgsRest(__VLS_61));
    __VLS_63.slots.default;
    if (__VLS_ctx.snapshot) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        const __VLS_64 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_65 = __VLS_asFunctionalComponent(__VLS_64, new __VLS_64({
            type: "success",
            size: "small",
            ...{ style: {} },
        }));
        const __VLS_66 = __VLS_65({
            type: "success",
            size: "small",
            ...{ style: {} },
        }, ...__VLS_functionalComponentArgsRest(__VLS_65));
        __VLS_67.slots.default;
        (__VLS_ctx.snapshot.branch || 'HEAD');
        var __VLS_67;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({
            ...{ class: "sha-box" },
        });
        (__VLS_ctx.snapshot.head ? __VLS_ctx.snapshot.head.slice(0, 8) : 'N/A');
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-muted" },
        });
    }
    var __VLS_63;
    const __VLS_68 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_69 = __VLS_asFunctionalComponent(__VLS_68, new __VLS_68({
        label: "关联工程 (Related Projects)",
    }));
    const __VLS_70 = __VLS_69({
        label: "关联工程 (Related Projects)",
    }, ...__VLS_functionalComponentArgsRest(__VLS_69));
    __VLS_71.slots.default;
    if (__VLS_ctx.project.related_projects && __VLS_ctx.project.related_projects.length > 0) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
        for (const [rel] of __VLS_getVForSourceType((__VLS_ctx.project.related_projects))) {
            const __VLS_72 = {}.ElTag;
            /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
            // @ts-ignore
            const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
                key: (rel),
                type: "primary",
                effect: "plain",
                ...{ style: {} },
            }));
            const __VLS_74 = __VLS_73({
                key: (rel),
                type: "primary",
                effect: "plain",
                ...{ style: {} },
            }, ...__VLS_functionalComponentArgsRest(__VLS_73));
            __VLS_75.slots.default;
            (rel);
            var __VLS_75;
        }
    }
    else {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-muted" },
        });
    }
    var __VLS_71;
    const __VLS_76 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_77 = __VLS_asFunctionalComponent(__VLS_76, new __VLS_76({
        label: "治理原则",
        span: (2),
    }));
    const __VLS_78 = __VLS_77({
        label: "治理原则",
        span: (2),
    }, ...__VLS_functionalComponentArgsRest(__VLS_77));
    __VLS_79.slots.default;
    const __VLS_80 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    const __VLS_81 = __VLS_asFunctionalComponent(__VLS_80, new __VLS_80({
        type: "danger",
        effect: "plain",
    }));
    const __VLS_82 = __VLS_81({
        type: "danger",
        effect: "plain",
    }, ...__VLS_functionalComponentArgsRest(__VLS_81));
    __VLS_83.slots.default;
    var __VLS_83;
    var __VLS_79;
    var __VLS_43;
    if (__VLS_ctx.snapshot) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "metrics-block" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.h4, __VLS_intrinsicElements.h4)({});
        const __VLS_84 = {}.ElRow;
        /** @type {[typeof __VLS_components.ElRow, typeof __VLS_components.elRow, typeof __VLS_components.ElRow, typeof __VLS_components.elRow, ]} */ ;
        // @ts-ignore
        const __VLS_85 = __VLS_asFunctionalComponent(__VLS_84, new __VLS_84({
            gutter: (16),
        }));
        const __VLS_86 = __VLS_85({
            gutter: (16),
        }, ...__VLS_functionalComponentArgsRest(__VLS_85));
        __VLS_87.slots.default;
        const __VLS_88 = {}.ElCol;
        /** @type {[typeof __VLS_components.ElCol, typeof __VLS_components.elCol, typeof __VLS_components.ElCol, typeof __VLS_components.elCol, ]} */ ;
        // @ts-ignore
        const __VLS_89 = __VLS_asFunctionalComponent(__VLS_88, new __VLS_88({
            span: (4),
        }));
        const __VLS_90 = __VLS_89({
            span: (4),
        }, ...__VLS_functionalComponentArgsRest(__VLS_89));
        __VLS_91.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-box" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-number text-primary" },
        });
        (__VLS_ctx.snapshot.file_count);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-title" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-sub" },
        });
        var __VLS_91;
        const __VLS_92 = {}.ElCol;
        /** @type {[typeof __VLS_components.ElCol, typeof __VLS_components.elCol, typeof __VLS_components.ElCol, typeof __VLS_components.elCol, ]} */ ;
        // @ts-ignore
        const __VLS_93 = __VLS_asFunctionalComponent(__VLS_92, new __VLS_92({
            span: (4),
        }));
        const __VLS_94 = __VLS_93({
            span: (4),
        }, ...__VLS_functionalComponentArgsRest(__VLS_93));
        __VLS_95.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-box" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-number text-info" },
        });
        (__VLS_ctx.snapshot.directory_count);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-title" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-sub" },
        });
        var __VLS_95;
        const __VLS_96 = {}.ElCol;
        /** @type {[typeof __VLS_components.ElCol, typeof __VLS_components.elCol, typeof __VLS_components.ElCol, typeof __VLS_components.elCol, ]} */ ;
        // @ts-ignore
        const __VLS_97 = __VLS_asFunctionalComponent(__VLS_96, new __VLS_96({
            span: (4),
        }));
        const __VLS_98 = __VLS_97({
            span: (4),
        }, ...__VLS_functionalComponentArgsRest(__VLS_97));
        __VLS_99.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-box" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-number text-warning" },
        });
        (__VLS_ctx.snapshot.dependency_count);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-title" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-sub" },
        });
        var __VLS_99;
        const __VLS_100 = {}.ElCol;
        /** @type {[typeof __VLS_components.ElCol, typeof __VLS_components.elCol, typeof __VLS_components.ElCol, typeof __VLS_components.elCol, ]} */ ;
        // @ts-ignore
        const __VLS_101 = __VLS_asFunctionalComponent(__VLS_100, new __VLS_100({
            span: (4),
        }));
        const __VLS_102 = __VLS_101({
            span: (4),
        }, ...__VLS_functionalComponentArgsRest(__VLS_101));
        __VLS_103.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-box" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-number text-success" },
        });
        (__VLS_ctx.project.entity_count);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-title" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-sub" },
        });
        var __VLS_103;
        const __VLS_104 = {}.ElCol;
        /** @type {[typeof __VLS_components.ElCol, typeof __VLS_components.elCol, typeof __VLS_components.ElCol, typeof __VLS_components.elCol, ]} */ ;
        // @ts-ignore
        const __VLS_105 = __VLS_asFunctionalComponent(__VLS_104, new __VLS_104({
            span: (4),
        }));
        const __VLS_106 = __VLS_105({
            span: (4),
        }, ...__VLS_functionalComponentArgsRest(__VLS_105));
        __VLS_107.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-box" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-number text-purple" },
        });
        (__VLS_ctx.project.relation_count);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-title" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-sub" },
        });
        var __VLS_107;
        const __VLS_108 = {}.ElCol;
        /** @type {[typeof __VLS_components.ElCol, typeof __VLS_components.elCol, typeof __VLS_components.ElCol, typeof __VLS_components.elCol, ]} */ ;
        // @ts-ignore
        const __VLS_109 = __VLS_asFunctionalComponent(__VLS_108, new __VLS_108({
            span: (4),
        }));
        const __VLS_110 = __VLS_109({
            span: (4),
        }, ...__VLS_functionalComponentArgsRest(__VLS_109));
        __VLS_111.slots.default;
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-box" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-number text-cyan" },
        });
        (__VLS_ctx.snapshot.frameworks.length);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-title" },
        });
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "stat-sub" },
        });
        var __VLS_111;
        var __VLS_87;
        if (__VLS_ctx.snapshot.frameworks && __VLS_ctx.snapshot.frameworks.length > 0) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "framework-section" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "sub-label" },
            });
            for (const [fw] of __VLS_getVForSourceType((__VLS_ctx.snapshot.frameworks))) {
                const __VLS_112 = {}.ElTooltip;
                /** @type {[typeof __VLS_components.ElTooltip, typeof __VLS_components.elTooltip, typeof __VLS_components.ElTooltip, typeof __VLS_components.elTooltip, ]} */ ;
                // @ts-ignore
                const __VLS_113 = __VLS_asFunctionalComponent(__VLS_112, new __VLS_112({
                    key: (fw.name),
                    placement: "top",
                }));
                const __VLS_114 = __VLS_113({
                    key: (fw.name),
                    placement: "top",
                }, ...__VLS_functionalComponentArgsRest(__VLS_113));
                __VLS_115.slots.default;
                {
                    const { content: __VLS_thisSlot } = __VLS_115.slots;
                    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({});
                    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
                    (fw.name);
                    ((fw.confidence * 100).toFixed(0));
                    __VLS_asFunctionalElement(__VLS_intrinsicElements.br)({});
                    (fw.version || '未指定');
                    __VLS_asFunctionalElement(__VLS_intrinsicElements.br)({});
                    __VLS_asFunctionalElement(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({});
                    (fw.evidence);
                }
                const __VLS_116 = {}.ElTag;
                /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
                // @ts-ignore
                const __VLS_117 = __VLS_asFunctionalComponent(__VLS_116, new __VLS_116({
                    size: "default",
                    effect: "light",
                    type: "success",
                    ...{ class: "fw-tag" },
                }));
                const __VLS_118 = __VLS_117({
                    size: "default",
                    effect: "light",
                    type: "success",
                    ...{ class: "fw-tag" },
                }, ...__VLS_functionalComponentArgsRest(__VLS_117));
                __VLS_119.slots.default;
                (fw.name);
                if (fw.version) {
                    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                        ...{ class: "fw-ver" },
                    });
                    (fw.version);
                }
                var __VLS_119;
                var __VLS_115;
            }
        }
        if (__VLS_ctx.snapshot.languages && __VLS_ctx.snapshot.languages.length > 0) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "language-section" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "sub-label" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "lang-bars" },
            });
            for (const [lang] of __VLS_getVForSourceType((__VLS_ctx.snapshot.languages.slice(0, 6)))) {
                __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                    key: (lang.name),
                    ...{ class: "lang-bar-item" },
                });
                __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                    ...{ class: "lang-header" },
                });
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "lang-name" },
                });
                (lang.name);
                __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                    ...{ class: "lang-pct" },
                });
                (lang.percentage);
                (lang.file_count);
                const __VLS_120 = {}.ElProgress;
                /** @type {[typeof __VLS_components.ElProgress, typeof __VLS_components.elProgress, ]} */ ;
                // @ts-ignore
                const __VLS_121 = __VLS_asFunctionalComponent(__VLS_120, new __VLS_120({
                    percentage: (lang.percentage),
                    showText: (false),
                    strokeWidth: (8),
                    color: (__VLS_ctx.getLanguageColor(lang.name)),
                }));
                const __VLS_122 = __VLS_121({
                    percentage: (lang.percentage),
                    showText: (false),
                    strokeWidth: (8),
                    color: (__VLS_ctx.getLanguageColor(lang.name)),
                }, ...__VLS_functionalComponentArgsRest(__VLS_121));
            }
        }
    }
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "tabs-block" },
    });
    const __VLS_124 = {}.ElTabs;
    /** @type {[typeof __VLS_components.ElTabs, typeof __VLS_components.elTabs, typeof __VLS_components.ElTabs, typeof __VLS_components.elTabs, ]} */ ;
    // @ts-ignore
    const __VLS_125 = __VLS_asFunctionalComponent(__VLS_124, new __VLS_124({
        modelValue: (__VLS_ctx.activeTab),
    }));
    const __VLS_126 = __VLS_125({
        modelValue: (__VLS_ctx.activeTab),
    }, ...__VLS_functionalComponentArgsRest(__VLS_125));
    __VLS_127.slots.default;
    const __VLS_128 = {}.ElTabPane;
    /** @type {[typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, ]} */ ;
    // @ts-ignore
    const __VLS_129 = __VLS_asFunctionalComponent(__VLS_128, new __VLS_128({
        label: "依赖明细 (Dependencies)",
        name: "dependencies",
    }));
    const __VLS_130 = __VLS_129({
        label: "依赖明细 (Dependencies)",
        name: "dependencies",
    }, ...__VLS_functionalComponentArgsRest(__VLS_129));
    __VLS_131.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "tab-filter-bar" },
    });
    const __VLS_132 = {}.ElInput;
    /** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
    // @ts-ignore
    const __VLS_133 = __VLS_asFunctionalComponent(__VLS_132, new __VLS_132({
        modelValue: (__VLS_ctx.depSearch),
        placeholder: "搜索依赖包名...",
        clearable: true,
        ...{ style: {} },
    }));
    const __VLS_134 = __VLS_133({
        modelValue: (__VLS_ctx.depSearch),
        placeholder: "搜索依赖包名...",
        clearable: true,
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_133));
    const __VLS_136 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    const __VLS_137 = __VLS_asFunctionalComponent(__VLS_136, new __VLS_136({
        type: "info",
    }));
    const __VLS_138 = __VLS_137({
        type: "info",
    }, ...__VLS_functionalComponentArgsRest(__VLS_137));
    __VLS_139.slots.default;
    (__VLS_ctx.filteredDependencies.length);
    var __VLS_139;
    const __VLS_140 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    const __VLS_141 = __VLS_asFunctionalComponent(__VLS_140, new __VLS_140({
        data: (__VLS_ctx.filteredDependencies),
        border: true,
        stripe: true,
        maxHeight: "400",
    }));
    const __VLS_142 = __VLS_141({
        data: (__VLS_ctx.filteredDependencies),
        border: true,
        stripe: true,
        maxHeight: "400",
    }, ...__VLS_functionalComponentArgsRest(__VLS_141));
    __VLS_143.slots.default;
    const __VLS_144 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_145 = __VLS_asFunctionalComponent(__VLS_144, new __VLS_144({
        prop: "name",
        label: "依赖包名称",
        width: "220",
    }));
    const __VLS_146 = __VLS_145({
        prop: "name",
        label: "依赖包名称",
        width: "220",
    }, ...__VLS_functionalComponentArgsRest(__VLS_145));
    __VLS_147.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_147.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
        (row.name);
    }
    var __VLS_147;
    const __VLS_148 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_149 = __VLS_asFunctionalComponent(__VLS_148, new __VLS_148({
        prop: "ecosystem",
        label: "生态系统",
        width: "120",
    }));
    const __VLS_150 = __VLS_149({
        prop: "ecosystem",
        label: "生态系统",
        width: "120",
    }, ...__VLS_functionalComponentArgsRest(__VLS_149));
    __VLS_151.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_151.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        const __VLS_152 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_153 = __VLS_asFunctionalComponent(__VLS_152, new __VLS_152({
            size: "small",
        }));
        const __VLS_154 = __VLS_153({
            size: "small",
        }, ...__VLS_functionalComponentArgsRest(__VLS_153));
        __VLS_155.slots.default;
        (row.ecosystem);
        var __VLS_155;
    }
    var __VLS_151;
    const __VLS_156 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_157 = __VLS_asFunctionalComponent(__VLS_156, new __VLS_156({
        prop: "version_spec",
        label: "版本规范",
        width: "150",
    }));
    const __VLS_158 = __VLS_157({
        prop: "version_spec",
        label: "版本规范",
        width: "150",
    }, ...__VLS_functionalComponentArgsRest(__VLS_157));
    __VLS_159.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_159.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({});
        (row.version_spec);
    }
    var __VLS_159;
    const __VLS_160 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_161 = __VLS_asFunctionalComponent(__VLS_160, new __VLS_160({
        prop: "scope",
        label: "作用域 (Scope)",
        width: "130",
    }));
    const __VLS_162 = __VLS_161({
        prop: "scope",
        label: "作用域 (Scope)",
        width: "130",
    }, ...__VLS_functionalComponentArgsRest(__VLS_161));
    __VLS_163.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_163.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        const __VLS_164 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_165 = __VLS_asFunctionalComponent(__VLS_164, new __VLS_164({
            size: "small",
            type: (row.scope === 'runtime' ? 'primary' : 'info'),
        }));
        const __VLS_166 = __VLS_165({
            size: "small",
            type: (row.scope === 'runtime' ? 'primary' : 'info'),
        }, ...__VLS_functionalComponentArgsRest(__VLS_165));
        __VLS_167.slots.default;
        (row.scope);
        var __VLS_167;
    }
    var __VLS_163;
    const __VLS_168 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_169 = __VLS_asFunctionalComponent(__VLS_168, new __VLS_168({
        prop: "manifest_path",
        label: "来源清单文件",
        minWidth: "260",
    }));
    const __VLS_170 = __VLS_169({
        prop: "manifest_path",
        label: "来源清单文件",
        minWidth: "260",
    }, ...__VLS_functionalComponentArgsRest(__VLS_169));
    __VLS_171.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_171.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "manifest-text" },
        });
        (row.manifest_path);
    }
    var __VLS_171;
    var __VLS_143;
    var __VLS_131;
    const __VLS_172 = {}.ElTabPane;
    /** @type {[typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, ]} */ ;
    // @ts-ignore
    const __VLS_173 = __VLS_asFunctionalComponent(__VLS_172, new __VLS_172({
        label: "摄取审计历史 (Ingestion Runs)",
        name: "runs",
    }));
    const __VLS_174 = __VLS_173({
        label: "摄取审计历史 (Ingestion Runs)",
        name: "runs",
    }, ...__VLS_functionalComponentArgsRest(__VLS_173));
    __VLS_175.slots.default;
    const __VLS_176 = {}.ElTable;
    /** @type {[typeof __VLS_components.ElTable, typeof __VLS_components.elTable, typeof __VLS_components.ElTable, typeof __VLS_components.elTable, ]} */ ;
    // @ts-ignore
    const __VLS_177 = __VLS_asFunctionalComponent(__VLS_176, new __VLS_176({
        data: (__VLS_ctx.scanRuns),
        border: true,
        stripe: true,
        maxHeight: "400",
    }));
    const __VLS_178 = __VLS_177({
        data: (__VLS_ctx.scanRuns),
        border: true,
        stripe: true,
        maxHeight: "400",
    }, ...__VLS_functionalComponentArgsRest(__VLS_177));
    __VLS_179.slots.default;
    const __VLS_180 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_181 = __VLS_asFunctionalComponent(__VLS_180, new __VLS_180({
        prop: "id",
        label: "Run ID",
        width: "120",
    }));
    const __VLS_182 = __VLS_181({
        prop: "id",
        label: "Run ID",
        width: "120",
    }, ...__VLS_functionalComponentArgsRest(__VLS_181));
    __VLS_183.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_183.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({});
        (row.id.slice(0, 8));
    }
    var __VLS_183;
    const __VLS_184 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_185 = __VLS_asFunctionalComponent(__VLS_184, new __VLS_184({
        prop: "status",
        label: "状态",
        width: "120",
    }));
    const __VLS_186 = __VLS_185({
        prop: "status",
        label: "状态",
        width: "120",
    }, ...__VLS_functionalComponentArgsRest(__VLS_185));
    __VLS_187.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_187.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        const __VLS_188 = {}.ElTag;
        /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
        // @ts-ignore
        const __VLS_189 = __VLS_asFunctionalComponent(__VLS_188, new __VLS_188({
            size: "small",
            type: (row.status === 'COMPLETED' ? 'success' : (row.status === 'RUNNING' ? 'warning' : 'danger')),
        }));
        const __VLS_190 = __VLS_189({
            size: "small",
            type: (row.status === 'COMPLETED' ? 'success' : (row.status === 'RUNNING' ? 'warning' : 'danger')),
        }, ...__VLS_functionalComponentArgsRest(__VLS_189));
        __VLS_191.slots.default;
        (row.status);
        var __VLS_191;
    }
    var __VLS_187;
    const __VLS_192 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_193 = __VLS_asFunctionalComponent(__VLS_192, new __VLS_192({
        prop: "started_at",
        label: "执行开始时间",
        width: "180",
    }));
    const __VLS_194 = __VLS_193({
        prop: "started_at",
        label: "执行开始时间",
        width: "180",
    }, ...__VLS_functionalComponentArgsRest(__VLS_193));
    __VLS_195.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_195.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        (__VLS_ctx.formatDate(row.started_at));
    }
    var __VLS_195;
    const __VLS_196 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_197 = __VLS_asFunctionalComponent(__VLS_196, new __VLS_196({
        label: "HEAD 演进",
        width: "180",
    }));
    const __VLS_198 = __VLS_197({
        label: "HEAD 演进",
        width: "180",
    }, ...__VLS_functionalComponentArgsRest(__VLS_197));
    __VLS_199.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_199.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({});
        (row.head_before ? row.head_before.slice(0, 7) : 'init');
        __VLS_asFunctionalElement(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({});
        (row.head_after ? row.head_after.slice(0, 7) : 'N/A');
    }
    var __VLS_199;
    const __VLS_200 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_201 = __VLS_asFunctionalComponent(__VLS_200, new __VLS_200({
        label: "文件变动统计",
        width: "180",
    }));
    const __VLS_202 = __VLS_201({
        label: "文件变动统计",
        width: "180",
    }, ...__VLS_functionalComponentArgsRest(__VLS_201));
    __VLS_203.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_203.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-success" },
        });
        (row.files_created);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-primary" },
        });
        (row.files_updated);
        __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
            ...{ class: "text-danger" },
        });
        (row.files_deleted);
    }
    var __VLS_203;
    const __VLS_204 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_205 = __VLS_asFunctionalComponent(__VLS_204, new __VLS_204({
        prop: "entities_created",
        label: "新增实体",
        width: "100",
    }));
    const __VLS_206 = __VLS_205({
        prop: "entities_created",
        label: "新增实体",
        width: "100",
    }, ...__VLS_functionalComponentArgsRest(__VLS_205));
    const __VLS_208 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_209 = __VLS_asFunctionalComponent(__VLS_208, new __VLS_208({
        prop: "relations_created",
        label: "新增关系",
        width: "100",
    }));
    const __VLS_210 = __VLS_209({
        prop: "relations_created",
        label: "新增关系",
        width: "100",
    }, ...__VLS_functionalComponentArgsRest(__VLS_209));
    const __VLS_212 = {}.ElTableColumn;
    /** @type {[typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, typeof __VLS_components.ElTableColumn, typeof __VLS_components.elTableColumn, ]} */ ;
    // @ts-ignore
    const __VLS_213 = __VLS_asFunctionalComponent(__VLS_212, new __VLS_212({
        label: "警告/错误",
        width: "120",
    }));
    const __VLS_214 = __VLS_213({
        label: "警告/错误",
        width: "120",
    }, ...__VLS_functionalComponentArgsRest(__VLS_213));
    __VLS_215.slots.default;
    {
        const { default: __VLS_thisSlot } = __VLS_215.slots;
        const [{ row }] = __VLS_getSlotParams(__VLS_thisSlot);
        if (row.warnings && row.warnings.length > 0) {
            const __VLS_216 = {}.ElTag;
            /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
            // @ts-ignore
            const __VLS_217 = __VLS_asFunctionalComponent(__VLS_216, new __VLS_216({
                type: "warning",
                size: "small",
            }));
            const __VLS_218 = __VLS_217({
                type: "warning",
                size: "small",
            }, ...__VLS_functionalComponentArgsRest(__VLS_217));
            __VLS_219.slots.default;
            (row.warnings.length);
            var __VLS_219;
        }
        if (row.errors && row.errors.length > 0) {
            const __VLS_220 = {}.ElTag;
            /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
            // @ts-ignore
            const __VLS_221 = __VLS_asFunctionalComponent(__VLS_220, new __VLS_220({
                type: "danger",
                size: "small",
                ...{ style: {} },
            }));
            const __VLS_222 = __VLS_221({
                type: "danger",
                size: "small",
                ...{ style: {} },
            }, ...__VLS_functionalComponentArgsRest(__VLS_221));
            __VLS_223.slots.default;
            (row.errors.length);
            var __VLS_223;
        }
        if ((!row.warnings || row.warnings.length === 0) && (!row.errors || row.errors.length === 0)) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "text-muted" },
            });
        }
    }
    var __VLS_215;
    var __VLS_179;
    var __VLS_175;
    const __VLS_224 = {}.ElTabPane;
    /** @type {[typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, typeof __VLS_components.ElTabPane, typeof __VLS_components.elTabPane, ]} */ ;
    // @ts-ignore
    const __VLS_225 = __VLS_asFunctionalComponent(__VLS_224, new __VLS_224({
        label: "原始配置与扩展属性 (Metadata)",
        name: "metadata",
    }));
    const __VLS_226 = __VLS_225({
        label: "原始配置与扩展属性 (Metadata)",
        name: "metadata",
    }, ...__VLS_functionalComponentArgsRest(__VLS_225));
    __VLS_227.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.pre, __VLS_intrinsicElements.pre)({
        ...{ class: "json-preview" },
    });
    (JSON.stringify(__VLS_ctx.project.metadata, null, 2));
    var __VLS_227;
    var __VLS_127;
    var __VLS_27;
}
/** @type {__VLS_StyleScopedClasses['project-detail-container']} */ ;
/** @type {__VLS_StyleScopedClasses['header-nav']} */ ;
/** @type {__VLS_StyleScopedClasses['header-actions']} */ ;
/** @type {__VLS_StyleScopedClasses['detail-card']} */ ;
/** @type {__VLS_StyleScopedClasses['card-header']} */ ;
/** @type {__VLS_StyleScopedClasses['title-area']} */ ;
/** @type {__VLS_StyleScopedClasses['project-name']} */ ;
/** @type {__VLS_StyleScopedClasses['path-box']} */ ;
/** @type {__VLS_StyleScopedClasses['sha-box']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['metrics-block']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-number']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-title']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-sub']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-number']} */ ;
/** @type {__VLS_StyleScopedClasses['text-info']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-title']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-sub']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-number']} */ ;
/** @type {__VLS_StyleScopedClasses['text-warning']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-title']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-sub']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-number']} */ ;
/** @type {__VLS_StyleScopedClasses['text-success']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-title']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-sub']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-number']} */ ;
/** @type {__VLS_StyleScopedClasses['text-purple']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-title']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-sub']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-box']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-number']} */ ;
/** @type {__VLS_StyleScopedClasses['text-cyan']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-title']} */ ;
/** @type {__VLS_StyleScopedClasses['stat-sub']} */ ;
/** @type {__VLS_StyleScopedClasses['framework-section']} */ ;
/** @type {__VLS_StyleScopedClasses['sub-label']} */ ;
/** @type {__VLS_StyleScopedClasses['fw-tag']} */ ;
/** @type {__VLS_StyleScopedClasses['fw-ver']} */ ;
/** @type {__VLS_StyleScopedClasses['language-section']} */ ;
/** @type {__VLS_StyleScopedClasses['sub-label']} */ ;
/** @type {__VLS_StyleScopedClasses['lang-bars']} */ ;
/** @type {__VLS_StyleScopedClasses['lang-bar-item']} */ ;
/** @type {__VLS_StyleScopedClasses['lang-header']} */ ;
/** @type {__VLS_StyleScopedClasses['lang-name']} */ ;
/** @type {__VLS_StyleScopedClasses['lang-pct']} */ ;
/** @type {__VLS_StyleScopedClasses['tabs-block']} */ ;
/** @type {__VLS_StyleScopedClasses['tab-filter-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['manifest-text']} */ ;
/** @type {__VLS_StyleScopedClasses['text-success']} */ ;
/** @type {__VLS_StyleScopedClasses['text-primary']} */ ;
/** @type {__VLS_StyleScopedClasses['text-danger']} */ ;
/** @type {__VLS_StyleScopedClasses['text-muted']} */ ;
/** @type {__VLS_StyleScopedClasses['json-preview']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            ArrowLeft: ArrowLeft,
            Connection: Connection,
            Refresh: Refresh,
            loading: loading,
            scanning: scanning,
            activeTab: activeTab,
            depSearch: depSearch,
            project: project,
            snapshot: snapshot,
            scanRuns: scanRuns,
            filteredDependencies: filteredDependencies,
            getLanguageColor: getLanguageColor,
            formatDate: formatDate,
            handleTriggerScan: handleTriggerScan,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
