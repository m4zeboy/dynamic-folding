// app.jsx — V1 Sereno adapted for pywebview
// Based on the design handoff prototype (df-v1.jsx).
// Mock data replaced by window.pywebview.api calls;
// pipeline simulation replaced by window._df callbacks from Python.

const V1_B = '#3B82F6';
const V1_BL = '#EFF6FF';
const V1_SAN = "'DM Sans', 'Segoe UI', system-ui, sans-serif";
const V1_MON = "'DM Mono', 'Consolas', 'Cascadia Code', monospace";
const STAGE_LABELS = {
  scan: 'Varrer estrutura',
  extractor: 'Indexar metadados',
  preprocess: 'Pré-processar texto',
  embedding: 'Gerar vetores',
  reducer: 'Reduzir dimensões',
  proposal: 'Gerar proposta',
  clustering: 'Agrupar arquivos',
  naming: 'Nomear categorias'
};

// ── Icons (Feather-style, stroke-based) ──────────────────────────────────────

const DFIcon = ({
  name,
  size = 16,
  color = 'currentColor',
  sw = 1.5
}) => {
  const paths = {
    folder: /*#__PURE__*/React.createElement("path", {
      d: "M2 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"
    }),
    folderOpen: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
      d: "M2 6a2 2 0 012-2h4l2 2h6a2 2 0 012 2v1H2V6z"
    }), /*#__PURE__*/React.createElement("path", {
      d: "M2 9h16l-1.5 8H3.5L2 9z"
    })),
    file: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
      d: "M13 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V9z"
    }), /*#__PURE__*/React.createElement("polyline", {
      points: "13 2 13 9 20 9"
    })),
    chevR: /*#__PURE__*/React.createElement("polyline", {
      points: "9 18 15 12 9 6"
    }),
    chevD: /*#__PURE__*/React.createElement("polyline", {
      points: "6 9 12 15 18 9"
    }),
    check: /*#__PURE__*/React.createElement("polyline", {
      points: "20 6 9 17 4 12"
    }),
    arrow: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("line", {
      x1: "5",
      y1: "12",
      x2: "19",
      y2: "12"
    }), /*#__PURE__*/React.createElement("polyline", {
      points: "12 5 19 12 12 19"
    })),
    home: /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("path", {
      d: "M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"
    }), /*#__PURE__*/React.createElement("polyline", {
      points: "9 22 9 12 15 12 15 22"
    })),
    star: /*#__PURE__*/React.createElement("polygon", {
      points: "12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"
    })
  };
  return /*#__PURE__*/React.createElement("svg", {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: color,
    strokeWidth: sw,
    strokeLinecap: "round",
    strokeLinejoin: "round"
  }, paths[name]);
};

// ── Brand mark ("Geometric Fold") ────────────────────────────────────────────

const DFLogo = ({
  size = 18,
  color = V1_B
}) => /*#__PURE__*/React.createElement("svg", {
  width: size,
  height: size,
  viewBox: "0 0 100 100",
  fill: "none",
  xmlns: "http://www.w3.org/2000/svg"
}, /*#__PURE__*/React.createElement("path", {
  d: "M20 20H60V40H80V80H40V60H20V20Z",
  fill: color,
  fillOpacity: "0.12"
}), /*#__PURE__*/React.createElement("path", {
  d: "M20 20L40 40V60H20V20Z",
  fill: color,
  fillOpacity: "0.8"
}), /*#__PURE__*/React.createElement("path", {
  d: "M40 40H60V60H40V40Z",
  fill: color,
  fillOpacity: "0.6"
}), /*#__PURE__*/React.createElement("path", {
  d: "M60 40H80V80H60V40Z",
  fill: color
}), /*#__PURE__*/React.createElement("path", {
  d: "M40 60H60V80H40V60Z",
  fill: color,
  fillOpacity: "0.4"
}));

// ── File tree (lazy-loading from Python) ─────────────────────────────────────

function V1Tree({
  node,
  depth = 0,
  selectedPath,
  onSelect
}) {
  const [open, setOpen] = React.useState(!!node.expanded);
  const [children, setChildren] = React.useState(node.children !== undefined ? node.children : null);
  const isDir = node.type === 'folder';
  const isSel = selectedPath === node.path;
  const indent = 8 + depth * 14;
  const handleClick = async () => {
    if (!isDir) return;
    onSelect(node.path, node.name);
    const newOpen = !open;
    setOpen(newOpen);
    if (newOpen && children === null) {
      try {
        const kids = await window.pywebview.api.list_directory(node.path);
        setChildren(kids.map(k => ({
          ...k,
          children: null
        })));
      } catch (e) {
        setChildren([]);
      }
    }
  };
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    onClick: handleClick,
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 4,
      padding: `2px 8px 2px ${indent}px`,
      borderRadius: 4,
      cursor: isDir ? 'pointer' : 'default',
      background: isSel ? V1_BL : 'transparent',
      color: isSel ? V1_B : '#374151',
      fontSize: 13,
      fontFamily: V1_SAN,
      userSelect: 'none'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 12,
      display: 'flex',
      opacity: 0.45
    }
  }, isDir ? open ? /*#__PURE__*/React.createElement(DFIcon, {
    name: "chevD",
    size: 11
  }) : /*#__PURE__*/React.createElement(DFIcon, {
    name: "chevR",
    size: 11
  }) : null), /*#__PURE__*/React.createElement("span", {
    style: {
      color: isDir ? '#F59E0B' : '#CBD5E1',
      display: 'flex'
    }
  }, /*#__PURE__*/React.createElement(DFIcon, {
    name: isDir ? open ? 'folderOpen' : 'folder' : 'file',
    size: 14,
    sw: 1.8
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap',
      flex: 1
    }
  }, node.name)), isDir && open && children !== null && children.map(c => /*#__PURE__*/React.createElement(V1Tree, {
    key: c.path,
    node: c,
    depth: depth + 1,
    selectedPath: selectedPath,
    onSelect: onSelect
  })), isDir && open && children === null && /*#__PURE__*/React.createElement("div", {
    style: {
      paddingLeft: indent + 20,
      fontSize: 12,
      color: '#9CA3AF',
      padding: '2px 8px 2px ' + (indent + 20) + 'px',
      fontFamily: V1_SAN
    }
  }, "\u2026"));
}

// ── Proposal tree (from real StructureProposal JSON) ─────────────────────────

function countTotalFiles(node) {
  return (node.files || []).length + (node.subfolders || []).reduce((acc, sub) => acc + countTotalFiles(sub), 0);
}
function buildProposalNodes(proposal) {
  if (!proposal) return [];
  // Separate normal folders from the Outros outlier bucket
  const normal = proposal.folders.filter(f => (f.display_name || f.name) !== 'Outros');
  const outlier = proposal.folders.find(f => (f.display_name || f.name) === 'Outros');
  const nodes = [...normal];

  // Merge outlier files + top-level orphans into a single "Outros" node
  const outrosFiles = [...(outlier ? outlier.files : []), ...(proposal.orphans || [])];
  const outrosSubs = outlier ? outlier.subfolders || [] : [];
  if (outrosFiles.length > 0 || outrosSubs.length > 0) {
    nodes.push({
      name: 'Outros',
      display_name: 'Outros',
      files: outrosFiles,
      subfolders: outrosSubs
    });
  }
  return nodes;
}
function V1PropNode({
  node,
  depth = 0
}) {
  const [open, setOpen] = React.useState(depth === 0);
  const name = node.display_name || node.name;
  const badge = countTotalFiles(node);
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    onClick: () => setOpen(o => !o),
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      padding: `3px 12px 3px ${12 + depth * 16}px`,
      cursor: 'pointer',
      fontSize: 13,
      fontFamily: V1_SAN,
      color: '#374151',
      userSelect: 'none'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 11,
      display: 'flex',
      opacity: 0.38
    }
  }, open ? /*#__PURE__*/React.createElement(DFIcon, {
    name: "chevD",
    size: 11
  }) : /*#__PURE__*/React.createElement(DFIcon, {
    name: "chevR",
    size: 11
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#F59E0B',
      display: 'flex'
    }
  }, /*#__PURE__*/React.createElement(DFIcon, {
    name: open ? 'folderOpen' : 'folder',
    size: 14,
    sw: 1.8
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      flex: 1
    }
  }, name), badge > 0 && /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 11,
      color: '#9CA3AF',
      background: '#F3F4F6',
      borderRadius: 10,
      padding: '1px 7px',
      flexShrink: 0
    }
  }, badge)), open && /*#__PURE__*/React.createElement(React.Fragment, null, (node.subfolders || []).map(sub => /*#__PURE__*/React.createElement(V1PropNode, {
    key: sub.name,
    node: sub,
    depth: depth + 1
  })), (node.files || []).map(f => /*#__PURE__*/React.createElement("div", {
    key: f,
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 4,
      padding: `2px 12px 2px ${12 + (depth + 1) * 16}px`,
      fontSize: 12,
      color: '#6B7280',
      fontFamily: V1_SAN
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      color: '#CBD5E1',
      display: 'flex'
    }
  }, /*#__PURE__*/React.createElement(DFIcon, {
    name: "file",
    size: 12,
    sw: 1.8
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, f)))));
}

// ── Main app ──────────────────────────────────────────────────────────────────

function V1App() {
  const [screen, setScreen] = React.useState('select');
  const [treeNodes, setTreeNodes] = React.useState([]);
  const [treeLoading, setTreeLoading] = React.useState(true);
  const [selectedPath, setSelectedPath] = React.useState(null);
  const [selectedName, setSelectedName] = React.useState('');
  const [stages, setStages] = React.useState([]);
  const [proposal, setProposal] = React.useState(null);
  const [pipelineError, setPipelineError] = React.useState(null);
  const stepIdx = screen === 'select' ? 0 : screen === 'process' ? 1 : 2;

  // Reset back to folder-selection without closing the window
  const resetToSelect = () => {
    setScreen('select');
    setStages([]);
    setProposal(null);
    setPipelineError(null);
    setSelectedPath(null);
    setSelectedName('');
  };

  // Register Python→JS bridge + initialise tree on mount
  React.useEffect(() => {
    // Register callbacks that Python will call via evaluate_js
    window._df = {
      onStageStart: name => {
        setStages(prev => [...prev, {
          name,
          label: STAGE_LABELS[name] || name,
          done: false
        }]);
      },
      onStageEnd: name => {
        setStages(prev => prev.map(s => s.name === name ? {
          ...s,
          done: true
        } : s));
      },
      onPipelineDone: proposalObj => {
        setProposal(proposalObj);
        setScreen('proposal');
      },
      onPipelineError: msg => {
        setPipelineError(msg);
        setScreen('select');
      }
    };
    const init = async () => {
      const api = window.pywebview.api;
      const home = await api.get_home_path();
      const initialRoot = await api.get_initial_root();
      const kids = await api.list_directory(home);
      const lastName = home.replace(/\\/g, '/').split('/').filter(Boolean).pop() || home;
      setTreeNodes([{
        name: lastName,
        path: home,
        type: 'folder',
        hasChildren: true,
        children: kids.map(k => ({
          ...k,
          children: null
        })),
        expanded: true
      }]);
      setTreeLoading(false);
      if (initialRoot) {
        const name = initialRoot.replace(/\\/g, '/').split('/').filter(Boolean).pop() || initialRoot;
        setSelectedPath(initialRoot);
        setSelectedName(name);
        setStages([]);
        setScreen('process');
        api.start_pipeline(initialRoot);
      }
    };
    if (window.pywebview) {
      init().catch(console.error);
    } else {
      window.addEventListener('pywebviewready', () => init().catch(console.error), {
        once: true
      });
    }
  }, []);
  const startPipeline = () => {
    if (!selectedPath) return;
    setStages([]);
    setPipelineError(null);
    setScreen('process');
    window.pywebview.api.start_pipeline(selectedPath);
  };

  // ── Layout ──────────────────────────────────────────────────────────────────

  return /*#__PURE__*/React.createElement("div", {
    style: {
      width: '100%',
      height: '100vh',
      background: '#FAFAF8',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: V1_SAN,
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      height: 42,
      background: '#fff',
      borderBottom: '1px solid #E5E7EB',
      display: 'flex',
      alignItems: 'center',
      padding: '0 16px',
      gap: 12,
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 7
    }
  }, /*#__PURE__*/React.createElement(DFLogo, {
    size: 18
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 14,
      color: '#111827',
      letterSpacing: '-0.02em',
      textTransform: 'lowercase'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 700
    }
  }, "dynamic"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontWeight: 400
    }
  }, "folding"))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginLeft: 'auto',
      display: 'flex',
      alignItems: 'center',
      gap: 6
    }
  }, ['Selecionar', 'Processar', 'Proposta'].map((label, i) => /*#__PURE__*/React.createElement(React.Fragment, {
    key: label
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 5,
      opacity: i > stepIdx ? 0.3 : 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 18,
      height: 18,
      borderRadius: 9,
      flexShrink: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: i < stepIdx ? V1_B : i === stepIdx ? V1_BL : '#F3F4F6',
      border: i === stepIdx ? `2px solid ${V1_B}` : 'none'
    }
  }, i < stepIdx && /*#__PURE__*/React.createElement(DFIcon, {
    name: "check",
    size: 10,
    color: "#fff",
    sw: 2.5
  }), i === stepIdx && /*#__PURE__*/React.createElement("div", {
    style: {
      width: 6,
      height: 6,
      borderRadius: 3,
      background: V1_B
    }
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      fontWeight: 500,
      color: i === stepIdx ? V1_B : '#6B7280'
    }
  }, label)), i < 2 && /*#__PURE__*/React.createElement("div", {
    style: {
      width: 14,
      height: 1,
      background: '#E5E7EB'
    }
  }))))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: 'flex',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 232,
      borderRight: '1px solid #E5E7EB',
      background: '#FAFAF8',
      display: 'flex',
      flexDirection: 'column',
      flexShrink: 0
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '10px 12px 5px',
      display: 'flex',
      alignItems: 'center',
      gap: 5
    }
  }, /*#__PURE__*/React.createElement(DFIcon, {
    name: "home",
    size: 11,
    color: "#9CA3AF"
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 10.5,
      fontWeight: 600,
      color: '#9CA3AF',
      textTransform: 'uppercase',
      letterSpacing: '0.07em'
    }
  }, "Explorador")), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      overflowY: 'auto',
      padding: '2px 4px 8px'
    }
  }, treeLoading ? /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '8px 12px',
      fontSize: 12,
      color: '#9CA3AF',
      fontFamily: V1_SAN
    }
  }, "Carregando\u2026") : treeNodes.map(n => /*#__PURE__*/React.createElement(V1Tree, {
    key: n.path,
    node: n,
    selectedPath: selectedPath,
    onSelect: (path, name) => {
      setSelectedPath(path);
      setSelectedName(name);
    }
  })))), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }
  }, screen === 'select' && /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 20,
      padding: 40
    }
  }, pipelineError && /*#__PURE__*/React.createElement("div", {
    style: {
      background: '#FEF2F2',
      border: '1px solid #FECACA',
      borderRadius: 8,
      padding: '10px 18px',
      color: '#DC2626',
      fontSize: 12,
      fontFamily: V1_MON,
      maxWidth: 400,
      textAlign: 'center'
    }
  }, "\u26A0 ", pipelineError), /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'center'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 16,
      fontWeight: 600,
      color: '#111827',
      marginBottom: 8,
      letterSpacing: '-0.01em'
    }
  }, "Selecionar pasta"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: '#6B7280',
      lineHeight: 1.55
    }
  }, "Escolha uma pasta no explorador \xE0 esquerda para organizar")), selectedPath ? /*#__PURE__*/React.createElement("div", {
    style: {
      background: V1_BL,
      border: `1px solid #BFDBFE`,
      borderRadius: 8,
      padding: '10px 18px',
      display: 'flex',
      alignItems: 'center',
      gap: 8,
      maxWidth: 380
    }
  }, /*#__PURE__*/React.createElement(DFIcon, {
    name: "folder",
    size: 15,
    color: V1_B,
    sw: 2
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 13,
      color: V1_B,
      fontWeight: 500,
      fontFamily: V1_MON,
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    }
  }, selectedPath)) : /*#__PURE__*/React.createElement("div", {
    style: {
      width: 180,
      height: 96,
      borderRadius: 10,
      border: '1.5px dashed #D1D5DB',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 6
    }
  }, /*#__PURE__*/React.createElement(DFIcon, {
    name: "folder",
    size: 22,
    color: "#D1D5DB",
    sw: 1.5
  }), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: '#D1D5DB'
    }
  }, "Nenhuma selecionada")), /*#__PURE__*/React.createElement("button", {
    onClick: startPipeline,
    style: {
      background: selectedPath ? V1_B : '#E5E7EB',
      color: selectedPath ? '#fff' : '#9CA3AF',
      border: 'none',
      borderRadius: 8,
      padding: '10px 28px',
      fontSize: 14,
      fontWeight: 600,
      cursor: selectedPath ? 'pointer' : 'default',
      fontFamily: V1_SAN,
      letterSpacing: '-0.01em',
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      transition: 'background .2s'
    }
  }, "Iniciar an\xE1lise ", /*#__PURE__*/React.createElement(DFIcon, {
    name: "arrow",
    size: 14,
    color: selectedPath ? '#fff' : '#9CA3AF',
    sw: 2
  }))), screen === 'process' && /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      padding: '28px 40px',
      overflowY: 'auto'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 15,
      fontWeight: 600,
      color: '#111827',
      marginBottom: 22,
      letterSpacing: '-0.01em'
    }
  }, "Analisando", ' ', /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: V1_MON,
      color: V1_B,
      fontWeight: 400,
      fontSize: 13
    }
  }, selectedPath)), stages.length === 0 && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      color: '#9CA3AF',
      fontFamily: V1_SAN
    }
  }, "Iniciando\u2026"), stages.map((s, i) => /*#__PURE__*/React.createElement("div", {
    key: s.name,
    style: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: 14,
      padding: '11px 0',
      borderBottom: i < stages.length - 1 ? '1px solid #F3F4F6' : 'none',
      transition: 'opacity .35s'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 22,
      height: 22,
      borderRadius: 11,
      flexShrink: 0,
      marginTop: 1,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: s.done ? V1_B : V1_BL,
      border: !s.done ? `2px solid ${V1_B}` : 'none'
    }
  }, s.done ? /*#__PURE__*/React.createElement(DFIcon, {
    name: "check",
    size: 11,
    color: "#fff",
    sw: 2.5
  }) : /*#__PURE__*/React.createElement("div", {
    style: {
      width: 7,
      height: 7,
      borderRadius: 4,
      background: V1_B,
      animation: 'dfpulse 1s infinite'
    }
  })), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 13,
      fontWeight: 500,
      color: '#111827'
    }
  }, s.label), s.done && /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: '#9CA3AF',
      marginTop: 3
    }
  }, "Conclu\xEDdo"))))), screen === 'proposal' && proposal && (() => {
    const normalCount = proposal.folders.filter(f => (f.display_name || f.name) !== 'Outros').length;
    const totalFiles = proposal.folders.reduce((a, f) => a + countTotalFiles(f), 0) + (proposal.orphans || []).length;
    return /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden'
      }
    }, /*#__PURE__*/React.createElement("div", {
      style: {
        padding: '10px 16px',
        borderBottom: '1px solid #E5E7EB',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        flexShrink: 0
      }
    }, /*#__PURE__*/React.createElement(DFIcon, {
      name: "star",
      size: 13,
      color: V1_B,
      sw: 2
    }), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 13,
        fontWeight: 600,
        color: '#111827'
      }
    }, "Proposta de organiza\xE7\xE3o"), /*#__PURE__*/React.createElement("span", {
      style: {
        fontSize: 12,
        color: '#9CA3AF',
        marginLeft: 2
      }
    }, normalCount, " ", normalCount === 1 ? 'categoria' : 'categorias', " \xB7 ", totalFiles, " ", totalFiles === 1 ? 'arquivo' : 'arquivos')), /*#__PURE__*/React.createElement("div", {
      style: {
        flex: 1,
        overflowY: 'auto',
        padding: '6px 0'
      }
    }, buildProposalNodes(proposal).map(n => /*#__PURE__*/React.createElement(V1PropNode, {
      key: n.display_name || n.name,
      node: n
    }))), /*#__PURE__*/React.createElement("div", {
      style: {
        borderTop: '1px solid #E5E7EB',
        padding: '10px 16px',
        display: 'flex',
        gap: 8,
        justifyContent: 'flex-end',
        flexShrink: 0
      }
    }, /*#__PURE__*/React.createElement("button", {
      onClick: resetToSelect,
      style: {
        background: 'transparent',
        border: '1px solid #E5E7EB',
        color: '#6B7280',
        borderRadius: 7,
        padding: '7px 18px',
        fontSize: 13,
        fontWeight: 500,
        cursor: 'pointer',
        fontFamily: 'inherit'
      }
    }, "Recome\xE7ar"), /*#__PURE__*/React.createElement("button", {
      onClick: () => window.pywebview.api.accept(),
      style: {
        background: V1_B,
        color: '#fff',
        border: 'none',
        borderRadius: 7,
        padding: '7px 20px',
        fontSize: 13,
        fontWeight: 600,
        cursor: 'pointer',
        fontFamily: 'inherit'
      }
    }, "Aplicar proposta")));
  })())), /*#__PURE__*/React.createElement("style", null, `
        @keyframes dfpulse { 0%, 100% { opacity: 1 } 50% { opacity: .3 } }
        *, *::before, *::after { box-sizing: border-box; }
        body { margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #E5E7EB; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #D1D5DB; }
        button { outline: none; }
        button:focus-visible { outline: 2px solid ${V1_B}; outline-offset: 2px; }
      `));
}
ReactDOM.createRoot(document.getElementById('root')).render(/*#__PURE__*/React.createElement(V1App, null));