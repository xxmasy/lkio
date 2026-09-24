import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import { Refresh, FullScreen } from '@element-plus/icons-vue';
import cytoscape from 'cytoscape';
import { api } from '@/api/client';
import { ElMessage } from 'element-plus';
const route = useRoute();
const cyContainer = ref(null);
let cy = null;
const loading = ref(true);
const projects = ref([]);
const selectedScope = ref('ALL');
const layoutName = ref('breadthfirst');
const currentMode = ref('SCOPE');
const focusedEntityKey = ref('');
const drawerVisible = ref(false);
const drawerTitle = ref('元素属性');
const selectedNode = ref(null);
const selectedEdge = ref(null);
const typeColors = {
    PROJECT: '#3b82f6',
    REPOSITORY: '#10b981',
    FRONTEND: '#f59e0b',
    BACKEND: '#8b5cf6',
    DEFAULT: '#64748b'
};
function getNodeTagType(type) {
    switch (type) {
        case 'PROJECT': return 'primary';
        case 'REPOSITORY': return 'success';
        case 'FRONTEND': return 'warning';
        case 'BACKEND': return 'danger';
        default: return 'info';
    }
}
function initCytoscape(graphData) {
    if (!cyContainer.value)
        return;
    const elements = [
        ...graphData.nodes.map(n => ({
            data: {
                ...n.data,
                color: typeColors[n.data.entity_type] || typeColors.DEFAULT
            }
        })),
        ...graphData.edges.map(e => ({
            data: {
                ...e.data,
            }
        }))
    ];
    if (cy) {
        cy.destroy();
    }
    cy = cytoscape({
        container: cyContainer.value,
        elements: elements,
        style: [
            {
                selector: 'node',
                style: {
                    'label': 'data(label)',
                    'background-color': 'data(color)',
                    'color': '#1e293b',
                    'font-size': '12px',
                    'font-weight': 'bold',
                    'text-valign': 'bottom',
                    'text-margin-y': 6,
                    'width': 44,
                    'height': 44,
                    'border-width': 3,
                    'border-color': '#ffffff',
                    'border-opacity': 0.8,
                }
            },
            {
                selector: 'node:selected',
                style: {
                    'border-width': 4,
                    'border-color': '#e11d48',
                    'width': 50,
                    'height': 50
                }
            },
            {
                selector: 'edge',
                style: {
                    'label': 'data(label)',
                    'font-size': '11px',
                    'color': '#475569',
                    'text-background-color': '#f8fafc',
                    'text-background-opacity': 0.9,
                    'text-background-padding': '3px',
                    'width': 2.5,
                    'line-color': '#94a3b8',
                    'target-arrow-color': '#94a3b8',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'arrow-scale': 1.2
                }
            },
            {
                selector: 'edge[predicate = "paired_with"]',
                style: {
                    'line-color': '#e11d48',
                    'target-arrow-color': '#e11d48',
                    'line-style': 'dashed',
                    'width': 3
                }
            }
        ],
        layout: getLayoutConfig(layoutName.value)
    });
    // Node click: open drawer
    cy.on('tap', 'node', (evt) => {
        const nodeData = evt.target.data();
        selectedNode.value = nodeData;
        selectedEdge.value = null;
        drawerTitle.value = `实体详情: ${nodeData.label}`;
        drawerVisible.value = true;
    });
    // Edge click: open drawer
    cy.on('tap', 'edge', (evt) => {
        const edgeData = evt.target.data();
        selectedEdge.value = edgeData;
        selectedNode.value = null;
        drawerTitle.value = `关系详情: ${edgeData.predicate}`;
        drawerVisible.value = true;
    });
    // Double click node: focus neighborhood
    cy.on('dblclick', 'node', (evt) => {
        const nodeData = evt.target.data();
        focusNeighbor(nodeData.id, nodeData.entity_key);
    });
}
function getLayoutConfig(name) {
    if (name === 'breadthfirst') {
        return {
            name: 'breadthfirst',
            directed: true,
            padding: 40,
            spacingFactor: 1.4,
            animate: true
        };
    }
    if (name === 'cose') {
        return {
            name: 'cose',
            animate: true,
            randomize: false,
            nodeRepulsion: () => 8000,
            idealEdgeLength: () => 120,
            padding: 40
        };
    }
    return {
        name: name,
        padding: 40,
        animate: true
    };
}
function applyLayout() {
    if (cy) {
        const layout = cy.layout(getLayoutConfig(layoutName.value));
        layout.run();
    }
}
function fitView() {
    if (cy) {
        cy.fit(undefined, 40);
    }
}
async function fetchGraphData() {
    loading.value = true;
    currentMode.value = 'SCOPE';
    try {
        let graphData;
        if (selectedScope.value === 'ALL') {
            graphData = await api.getOverviewGraph();
        }
        else {
            graphData = await api.getProjectGraph(selectedScope.value);
        }
        await nextTick();
        initCytoscape(graphData);
    }
    catch (err) {
        ElMessage.error(`加载图谱数据失败: ${err.message}`);
    }
    finally {
        loading.value = false;
    }
}
function handleScopeChange(val) {
    selectedScope.value = val;
    fetchGraphData();
}
async function focusNeighbor(entityId, entityKey) {
    loading.value = true;
    currentMode.value = 'NEIGHBOR';
    focusedEntityKey.value = entityKey;
    drawerVisible.value = false;
    try {
        const neighborGraph = await api.getEntityNeighbors(entityId);
        await nextTick();
        initCytoscape(neighborGraph);
    }
    catch (err) {
        ElMessage.error(`加载邻域图谱失败: ${err.message}`);
    }
    finally {
        loading.value = false;
    }
}
onMounted(async () => {
    try {
        projects.value = await api.getProjects();
        const queryProj = route.query.project;
        if (queryProj && projects.value.some(p => p.key === queryProj)) {
            selectedScope.value = queryProj;
        }
        await fetchGraphData();
    }
    catch (err) {
        ElMessage.error(`初始化页面失败: ${err.message}`);
    }
});
onBeforeUnmount(() => {
    if (cy) {
        cy.destroy();
        cy = null;
    }
});
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "graph-page-container" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "graph-toolbar" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "toolbar-left" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "toolbar-label" },
});
const __VLS_0 = {}.ElSelect;
/** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    ...{ 'onChange': {} },
    modelValue: (__VLS_ctx.selectedScope),
    placeholder: "选择查看范围",
    ...{ style: {} },
}));
const __VLS_2 = __VLS_1({
    ...{ 'onChange': {} },
    modelValue: (__VLS_ctx.selectedScope),
    placeholder: "选择查看范围",
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
let __VLS_4;
let __VLS_5;
let __VLS_6;
const __VLS_7 = {
    onChange: (__VLS_ctx.handleScopeChange)
};
__VLS_3.slots.default;
const __VLS_8 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_9 = __VLS_asFunctionalComponent(__VLS_8, new __VLS_8({
    label: "🌐 全景概览 (All Projects)",
    value: "ALL",
}));
const __VLS_10 = __VLS_9({
    label: "🌐 全景概览 (All Projects)",
    value: "ALL",
}, ...__VLS_functionalComponentArgsRest(__VLS_9));
for (const [p] of __VLS_getVForSourceType((__VLS_ctx.projects))) {
    const __VLS_12 = {}.ElOption;
    /** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
    // @ts-ignore
    const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
        key: (p.key),
        label: (`${p.name} (${p.key})`),
        value: (p.key),
    }));
    const __VLS_14 = __VLS_13({
        key: (p.key),
        label: (`${p.name} (${p.key})`),
        value: (p.key),
    }, ...__VLS_functionalComponentArgsRest(__VLS_13));
}
var __VLS_3;
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "toolbar-label" },
    ...{ style: {} },
});
const __VLS_16 = {}.ElRadioGroup;
/** @type {[typeof __VLS_components.ElRadioGroup, typeof __VLS_components.elRadioGroup, typeof __VLS_components.ElRadioGroup, typeof __VLS_components.elRadioGroup, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
    ...{ 'onChange': {} },
    modelValue: (__VLS_ctx.layoutName),
    size: "small",
}));
const __VLS_18 = __VLS_17({
    ...{ 'onChange': {} },
    modelValue: (__VLS_ctx.layoutName),
    size: "small",
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
let __VLS_20;
let __VLS_21;
let __VLS_22;
const __VLS_23 = {
    onChange: (__VLS_ctx.applyLayout)
};
__VLS_19.slots.default;
const __VLS_24 = {}.ElRadioButton;
/** @type {[typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, ]} */ ;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
    value: "breadthfirst",
}));
const __VLS_26 = __VLS_25({
    value: "breadthfirst",
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
__VLS_27.slots.default;
var __VLS_27;
const __VLS_28 = {}.ElRadioButton;
/** @type {[typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, ]} */ ;
// @ts-ignore
const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
    value: "cose",
}));
const __VLS_30 = __VLS_29({
    value: "cose",
}, ...__VLS_functionalComponentArgsRest(__VLS_29));
__VLS_31.slots.default;
var __VLS_31;
const __VLS_32 = {}.ElRadioButton;
/** @type {[typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, typeof __VLS_components.ElRadioButton, typeof __VLS_components.elRadioButton, ]} */ ;
// @ts-ignore
const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
    value: "circle",
}));
const __VLS_34 = __VLS_33({
    value: "circle",
}, ...__VLS_functionalComponentArgsRest(__VLS_33));
__VLS_35.slots.default;
var __VLS_35;
var __VLS_19;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "toolbar-right" },
});
const __VLS_36 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
    ...{ 'onClick': {} },
    size: "small",
    icon: (__VLS_ctx.Refresh),
}));
const __VLS_38 = __VLS_37({
    ...{ 'onClick': {} },
    size: "small",
    icon: (__VLS_ctx.Refresh),
}, ...__VLS_functionalComponentArgsRest(__VLS_37));
let __VLS_40;
let __VLS_41;
let __VLS_42;
const __VLS_43 = {
    onClick: (__VLS_ctx.fetchGraphData)
};
__VLS_39.slots.default;
var __VLS_39;
const __VLS_44 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
    ...{ 'onClick': {} },
    size: "small",
    icon: (__VLS_ctx.FullScreen),
}));
const __VLS_46 = __VLS_45({
    ...{ 'onClick': {} },
    size: "small",
    icon: (__VLS_ctx.FullScreen),
}, ...__VLS_functionalComponentArgsRest(__VLS_45));
let __VLS_48;
let __VLS_49;
let __VLS_50;
const __VLS_51 = {
    onClick: (__VLS_ctx.fitView)
};
__VLS_47.slots.default;
var __VLS_47;
if (__VLS_ctx.currentMode === 'NEIGHBOR') {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "neighbor-banner" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    (__VLS_ctx.focusedEntityKey);
    const __VLS_52 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
        ...{ 'onClick': {} },
        type: "primary",
        link: true,
        size: "small",
    }));
    const __VLS_54 = __VLS_53({
        ...{ 'onClick': {} },
        type: "primary",
        link: true,
        size: "small",
    }, ...__VLS_functionalComponentArgsRest(__VLS_53));
    let __VLS_56;
    let __VLS_57;
    let __VLS_58;
    const __VLS_59 = {
        onClick: (...[$event]) => {
            if (!(__VLS_ctx.currentMode === 'NEIGHBOR'))
                return;
            __VLS_ctx.handleScopeChange(__VLS_ctx.selectedScope);
        }
    };
    __VLS_55.slots.default;
    var __VLS_55;
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "graph-wrapper" },
});
__VLS_asFunctionalDirective(__VLS_directives.vLoading)(null, { ...__VLS_directiveBindingRestFields, value: (__VLS_ctx.loading) }, null, null);
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ref: "cyContainer",
    ...{ class: "cy-canvas" },
});
/** @type {typeof __VLS_ctx.cyContainer} */ ;
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "graph-legend" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "legend-title" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "legend-item" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "legend-badge bg-project" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "legend-item" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "legend-badge bg-repo" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "legend-item" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "legend-badge bg-frontend" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "legend-item" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "legend-badge bg-backend" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "legend-desc" },
});
const __VLS_60 = {}.ElDrawer;
/** @type {[typeof __VLS_components.ElDrawer, typeof __VLS_components.elDrawer, typeof __VLS_components.ElDrawer, typeof __VLS_components.elDrawer, ]} */ ;
// @ts-ignore
const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
    modelValue: (__VLS_ctx.drawerVisible),
    title: (__VLS_ctx.drawerTitle),
    direction: "rtl",
    size: "380px",
}));
const __VLS_62 = __VLS_61({
    modelValue: (__VLS_ctx.drawerVisible),
    title: (__VLS_ctx.drawerTitle),
    direction: "rtl",
    size: "380px",
}, ...__VLS_functionalComponentArgsRest(__VLS_61));
__VLS_63.slots.default;
if (__VLS_ctx.selectedNode) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drawer-content" },
    });
    const __VLS_64 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    const __VLS_65 = __VLS_asFunctionalComponent(__VLS_64, new __VLS_64({
        type: (__VLS_ctx.getNodeTagType(__VLS_ctx.selectedNode.entity_type)),
        size: "large",
        effect: "dark",
    }));
    const __VLS_66 = __VLS_65({
        type: (__VLS_ctx.getNodeTagType(__VLS_ctx.selectedNode.entity_type)),
        size: "large",
        effect: "dark",
    }, ...__VLS_functionalComponentArgsRest(__VLS_65));
    __VLS_67.slots.default;
    (__VLS_ctx.selectedNode.entity_type);
    var __VLS_67;
    const __VLS_68 = {}.ElDescriptions;
    /** @type {[typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, ]} */ ;
    // @ts-ignore
    const __VLS_69 = __VLS_asFunctionalComponent(__VLS_68, new __VLS_68({
        column: (1),
        border: true,
        ...{ style: {} },
    }));
    const __VLS_70 = __VLS_69({
        column: (1),
        border: true,
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_69));
    __VLS_71.slots.default;
    const __VLS_72 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_73 = __VLS_asFunctionalComponent(__VLS_72, new __VLS_72({
        label: "名称",
    }));
    const __VLS_74 = __VLS_73({
        label: "名称",
    }, ...__VLS_functionalComponentArgsRest(__VLS_73));
    __VLS_75.slots.default;
    (__VLS_ctx.selectedNode.label);
    var __VLS_75;
    const __VLS_76 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_77 = __VLS_asFunctionalComponent(__VLS_76, new __VLS_76({
        label: "Entity Key",
    }));
    const __VLS_78 = __VLS_77({
        label: "Entity Key",
    }, ...__VLS_functionalComponentArgsRest(__VLS_77));
    __VLS_79.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({});
    (__VLS_ctx.selectedNode.entity_key);
    var __VLS_79;
    const __VLS_80 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_81 = __VLS_asFunctionalComponent(__VLS_80, new __VLS_80({
        label: "规范名称",
    }));
    const __VLS_82 = __VLS_81({
        label: "规范名称",
    }, ...__VLS_functionalComponentArgsRest(__VLS_81));
    __VLS_83.slots.default;
    (__VLS_ctx.selectedNode.canonical_name);
    var __VLS_83;
    const __VLS_84 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_85 = __VLS_asFunctionalComponent(__VLS_84, new __VLS_84({
        label: "路径",
    }));
    const __VLS_86 = __VLS_85({
        label: "路径",
    }, ...__VLS_functionalComponentArgsRest(__VLS_85));
    __VLS_87.slots.default;
    (__VLS_ctx.selectedNode.path || 'N/A');
    var __VLS_87;
    const __VLS_88 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_89 = __VLS_asFunctionalComponent(__VLS_88, new __VLS_88({
        label: "状态",
    }));
    const __VLS_90 = __VLS_89({
        label: "状态",
    }, ...__VLS_functionalComponentArgsRest(__VLS_89));
    __VLS_91.slots.default;
    (__VLS_ctx.selectedNode.status);
    var __VLS_91;
    var __VLS_71;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ style: {} },
    });
    const __VLS_92 = {}.ElButton;
    /** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
    // @ts-ignore
    const __VLS_93 = __VLS_asFunctionalComponent(__VLS_92, new __VLS_92({
        ...{ 'onClick': {} },
        type: "primary",
        ...{ style: {} },
    }));
    const __VLS_94 = __VLS_93({
        ...{ 'onClick': {} },
        type: "primary",
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_93));
    let __VLS_96;
    let __VLS_97;
    let __VLS_98;
    const __VLS_99 = {
        onClick: (...[$event]) => {
            if (!(__VLS_ctx.selectedNode))
                return;
            __VLS_ctx.focusNeighbor(__VLS_ctx.selectedNode.id, __VLS_ctx.selectedNode.entity_key);
        }
    };
    __VLS_95.slots.default;
    var __VLS_95;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "meta-section" },
        ...{ style: {} },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.pre, __VLS_intrinsicElements.pre)({
        ...{ class: "json-box" },
    });
    (JSON.stringify(__VLS_ctx.selectedNode.metadata, null, 2));
}
if (__VLS_ctx.selectedEdge) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "drawer-content" },
    });
    const __VLS_100 = {}.ElTag;
    /** @type {[typeof __VLS_components.ElTag, typeof __VLS_components.elTag, typeof __VLS_components.ElTag, typeof __VLS_components.elTag, ]} */ ;
    // @ts-ignore
    const __VLS_101 = __VLS_asFunctionalComponent(__VLS_100, new __VLS_100({
        type: "info",
        size: "large",
        effect: "dark",
    }));
    const __VLS_102 = __VLS_101({
        type: "info",
        size: "large",
        effect: "dark",
    }, ...__VLS_functionalComponentArgsRest(__VLS_101));
    __VLS_103.slots.default;
    var __VLS_103;
    const __VLS_104 = {}.ElDescriptions;
    /** @type {[typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, typeof __VLS_components.ElDescriptions, typeof __VLS_components.elDescriptions, ]} */ ;
    // @ts-ignore
    const __VLS_105 = __VLS_asFunctionalComponent(__VLS_104, new __VLS_104({
        column: (1),
        border: true,
        ...{ style: {} },
    }));
    const __VLS_106 = __VLS_105({
        column: (1),
        border: true,
        ...{ style: {} },
    }, ...__VLS_functionalComponentArgsRest(__VLS_105));
    __VLS_107.slots.default;
    const __VLS_108 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_109 = __VLS_asFunctionalComponent(__VLS_108, new __VLS_108({
        label: "谓词 (Predicate)",
    }));
    const __VLS_110 = __VLS_109({
        label: "谓词 (Predicate)",
    }, ...__VLS_functionalComponentArgsRest(__VLS_109));
    __VLS_111.slots.default;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.code, __VLS_intrinsicElements.code)({});
    (__VLS_ctx.selectedEdge.predicate);
    var __VLS_111;
    const __VLS_112 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_113 = __VLS_asFunctionalComponent(__VLS_112, new __VLS_112({
        label: "置信度 (Confidence)",
    }));
    const __VLS_114 = __VLS_113({
        label: "置信度 (Confidence)",
    }, ...__VLS_functionalComponentArgsRest(__VLS_113));
    __VLS_115.slots.default;
    const __VLS_116 = {}.ElProgress;
    /** @type {[typeof __VLS_components.ElProgress, typeof __VLS_components.elProgress, ]} */ ;
    // @ts-ignore
    const __VLS_117 = __VLS_asFunctionalComponent(__VLS_116, new __VLS_116({
        percentage: (Math.round(__VLS_ctx.selectedEdge.confidence * 100)),
    }));
    const __VLS_118 = __VLS_117({
        percentage: (Math.round(__VLS_ctx.selectedEdge.confidence * 100)),
    }, ...__VLS_functionalComponentArgsRest(__VLS_117));
    var __VLS_115;
    const __VLS_120 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_121 = __VLS_asFunctionalComponent(__VLS_120, new __VLS_120({
        label: "起点 (Source ID)",
    }));
    const __VLS_122 = __VLS_121({
        label: "起点 (Source ID)",
    }, ...__VLS_functionalComponentArgsRest(__VLS_121));
    __VLS_123.slots.default;
    (__VLS_ctx.selectedEdge.source);
    var __VLS_123;
    const __VLS_124 = {}.ElDescriptionsItem;
    /** @type {[typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, typeof __VLS_components.ElDescriptionsItem, typeof __VLS_components.elDescriptionsItem, ]} */ ;
    // @ts-ignore
    const __VLS_125 = __VLS_asFunctionalComponent(__VLS_124, new __VLS_124({
        label: "终点 (Target ID)",
    }));
    const __VLS_126 = __VLS_125({
        label: "终点 (Target ID)",
    }, ...__VLS_functionalComponentArgsRest(__VLS_125));
    __VLS_127.slots.default;
    (__VLS_ctx.selectedEdge.target);
    var __VLS_127;
    var __VLS_107;
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "meta-section" },
        ...{ style: {} },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.strong, __VLS_intrinsicElements.strong)({});
    __VLS_asFunctionalElement(__VLS_intrinsicElements.pre, __VLS_intrinsicElements.pre)({
        ...{ class: "json-box" },
    });
    (JSON.stringify(__VLS_ctx.selectedEdge.metadata, null, 2));
}
var __VLS_63;
/** @type {__VLS_StyleScopedClasses['graph-page-container']} */ ;
/** @type {__VLS_StyleScopedClasses['graph-toolbar']} */ ;
/** @type {__VLS_StyleScopedClasses['toolbar-left']} */ ;
/** @type {__VLS_StyleScopedClasses['toolbar-label']} */ ;
/** @type {__VLS_StyleScopedClasses['toolbar-label']} */ ;
/** @type {__VLS_StyleScopedClasses['toolbar-right']} */ ;
/** @type {__VLS_StyleScopedClasses['neighbor-banner']} */ ;
/** @type {__VLS_StyleScopedClasses['graph-wrapper']} */ ;
/** @type {__VLS_StyleScopedClasses['cy-canvas']} */ ;
/** @type {__VLS_StyleScopedClasses['graph-legend']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-title']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-project']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-repo']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-frontend']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-item']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-badge']} */ ;
/** @type {__VLS_StyleScopedClasses['bg-backend']} */ ;
/** @type {__VLS_StyleScopedClasses['legend-desc']} */ ;
/** @type {__VLS_StyleScopedClasses['drawer-content']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-section']} */ ;
/** @type {__VLS_StyleScopedClasses['json-box']} */ ;
/** @type {__VLS_StyleScopedClasses['drawer-content']} */ ;
/** @type {__VLS_StyleScopedClasses['meta-section']} */ ;
/** @type {__VLS_StyleScopedClasses['json-box']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            Refresh: Refresh,
            FullScreen: FullScreen,
            cyContainer: cyContainer,
            loading: loading,
            projects: projects,
            selectedScope: selectedScope,
            layoutName: layoutName,
            currentMode: currentMode,
            focusedEntityKey: focusedEntityKey,
            drawerVisible: drawerVisible,
            drawerTitle: drawerTitle,
            selectedNode: selectedNode,
            selectedEdge: selectedEdge,
            getNodeTagType: getNodeTagType,
            applyLayout: applyLayout,
            fitView: fitView,
            fetchGraphData: fetchGraphData,
            handleScopeChange: handleScopeChange,
            focusNeighbor: focusNeighbor,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
