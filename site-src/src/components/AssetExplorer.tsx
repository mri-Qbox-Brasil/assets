import React, { useEffect, useState, useRef, useCallback } from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import {
    Folder,
    FileText,
    Search,
    Home,
    ChevronRight,
    Copy,
    Link as LinkIcon,
    Download,
    Check,
    X,
    Maximize2
} from 'lucide-react';


import { VirtuosoGrid } from 'react-virtuoso';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const CDN_BASE = 'https://assets.mriqbox.com.br';

// Types matching the new generate_manifest.py output
interface FileVariant {
  ext: string;
  path: string;
  size: number;
}

interface AssetNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  baseName?: string;
  variants?: FileVariant[];
  ext?: string;
  children?: AssetNode[];
}

interface ManifestStats {
  total_files: number;
  total_size: number;
}

interface Manifest {
  root: AssetNode[];
  generated_at: string;
  stats?: ManifestStats;
}

function formatSize(bytes: number): string {
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

function getExtBadgeColor(ext: string): string {
  switch (ext) {
    case '.webp': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
    case '.png': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
    case '.jpg':
    case '.jpeg': return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
    case '.gif': return 'bg-purple-500/20 text-purple-400 border-purple-500/30';
    case '.svg': return 'bg-pink-500/20 text-pink-400 border-pink-500/30';
    default: return 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30';
  }
}

export const AssetExplorer: React.FC = () => {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [currentPath, setCurrentPath] = useState<string[]>([]);
  const [currentNode, setCurrentNode] = useState<AssetNode[] | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedState, setCopiedState] = useState<string | null>(null);
  const [previewImage, setPreviewImage] = useState<{path: string, name: string, variants?: FileVariant[]} | null>(null);
  const [expandedCopyId, setExpandedCopyId] = useState<string | null>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch('/manifest.json')
      .then(res => res.json())
      .then((data: Manifest) => {
        setManifest(data);
        // Initialize from hash if present
        const hash = window.location.hash.replace(/^#/, '');
        if (hash) {
            const parts = hash.split('/').filter(Boolean).map(p => decodeURIComponent(p));
            setCurrentPath(parts);
            
            let currentNodes = data.root;
            for (const part of parts) {
                const folder = currentNodes.find(n => n.name === part && n.type === 'directory');
                if (folder && folder.children) {
                    currentNodes = folder.children;
                } else {
                    // Invalid path in hash, reset to root
                    setCurrentPath([]);
                    currentNodes = data.root;
                    window.location.hash = '';
                    break;
                }
            }
            setCurrentNode(currentNodes);
        } else {
            setCurrentNode(data.root);
        }
      })
      .catch(err => console.error("Failed to load manifest", err));
  }, []);

  // Sync hash when path changes (except when triggered by hashchange)
  useEffect(() => {
    const currentHash = window.location.hash.replace(/^#/, '');
    const pathHash = currentPath.map(p => encodeURIComponent(p)).join('/');
    if (currentHash !== pathHash) {
        window.location.hash = pathHash;
    }
  }, [currentPath]);

  // Handle browser back/forward buttons
  useEffect(() => {
    const handleHashChange = () => {
        if (!manifest) return;
        const hash = window.location.hash.replace(/^#/, '');
        const parts = hash.split('/').filter(Boolean).map(p => decodeURIComponent(p));
        
        // Only update if hash is different from current state
        const currentPathStr = currentPath.join('/');
        const newPathStr = parts.join('/');
        
        if (currentPathStr !== newPathStr) {
            setCurrentPath(parts);
            let currentPathNodes = manifest.root;
            for (const part of parts) {
                const folder = currentPathNodes.find(n => n.name === part && n.type === 'directory');
                if (folder && folder.children) {
                    currentPathNodes = folder.children;
                }
            }
            setCurrentNode(currentPathNodes);
            setSearchQuery('');
        }
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, [manifest, currentPath]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (previewImage) {
          setPreviewImage(null);
        } else if (expandedCopyId) {
          setExpandedCopyId(null);
        }
      }
      // Ctrl+K / Cmd+K to focus search
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [previewImage, expandedCopyId]);

  // Click outside to collapse expanded copy buttons
  useEffect(() => {
    if (!expandedCopyId) return;
    const handleClick = () => setExpandedCopyId(null);
    window.addEventListener('click', handleClick);
    return () => window.removeEventListener('click', handleClick);
  }, [expandedCopyId]);

  const navigateTo = (folderName: string) => {
    const folder = currentNode?.find(n => n.name === folderName && n.type === 'directory');
    if (folder && folder.children) {
      const newPath = [...currentPath, folderName];
      setCurrentPath(newPath);
      setCurrentNode(folder.children);
      setSearchQuery('');
    }
  };

  const navigateUp = (levelIndex: number) => {
      if (!manifest) return;
      const newPath = currentPath.slice(0, levelIndex + 1);
      setCurrentPath(newPath);

      let nodes = manifest.root;
      for (const part of newPath) {
          const folder = nodes.find(n => n.name === part);
          if (folder && folder.children) {
              nodes = folder.children;
          }
      }
      setCurrentNode(nodes);
      setSearchQuery('');
  };

  const navigateRoot = () => {
      if (!manifest) return;
      setCurrentPath([]);
      setCurrentNode(manifest.root);
      setSearchQuery('');
      window.location.hash = '';
  }

  const copyToClipboard = useCallback((text: string, id: string, e: React.MouseEvent) => {
      e.stopPropagation();
      navigator.clipboard.writeText(text).then(() => {
          setCopiedState(id);
          setTimeout(() => setCopiedState(null), 2000);
      });
  }, []);

  const toggleCopyExpand = useCallback((id: string, e: React.MouseEvent) => {
      e.stopPropagation();
      setExpandedCopyId(prev => prev === id ? null : id);
  }, []);

  if (!manifest) return <div className="min-h-screen flex items-center justify-center text-zinc-400">Carregando arquivos...</div>;
  if (!currentNode) return <div className="min-h-screen flex items-center justify-center text-zinc-400">Iniciando...</div>;

  // With the new manifest format, deduplication is already done server-side.
  // Files with variants are already grouped. We just filter by search query.
  const processNodes = (nodes: AssetNode[], query: string) => {
      let filtered = nodes;
      if (query) {
          filtered = nodes.filter(item => {
              const searchName = item.baseName || item.name;
              return searchName.toLowerCase().includes(query.toLowerCase());
          });
      }

      const directories = filtered.filter(n => n.type === 'directory');
      const files = filtered.filter(n => n.type === 'file');

      // Sort files alphabetically
      files.sort((a, b) => (a.baseName || a.name).localeCompare(b.baseName || b.name));

      return [...directories, ...files];
  };

  const visibleItems = processNodes(currentNode, searchQuery);

  return (
    <div className="w-full min-h-screen bg-zinc-950 text-zinc-100 font-sans selection:bg-emerald-500/30">
        {/* Sticky Header */}
      <header className="sticky top-0 z-50 w-full border-b border-zinc-800/50 bg-zinc-950/80 backdrop-blur-xl supports-[backdrop-filter]:bg-zinc-950/60">
        <div className="w-full max-w-[1920px] mx-auto px-6 h-16 flex items-center justify-between gap-4">
            <h1 className="text-xl font-bold flex items-center gap-2 tracking-tight">
                <span className="text-emerald-500">mri</span>
                <span className="text-zinc-200">Qbox Assets</span>
            </h1>

            {/* Search Bar */}
            <div className="relative w-full max-w-md group">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 w-4 h-4 group-focus-within:text-emerald-500 transition-colors" />
                <input
                    ref={searchInputRef}
                    id="search-input"
                    type="text"
                    placeholder="Pesquisar..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-zinc-900/50 border border-zinc-800/50 rounded-lg py-2 pl-10 pr-12 text-sm focus:outline-none focus:border-emerald-500/50 focus:ring-4 focus:ring-emerald-500/10 transition-all placeholder-zinc-600 text-zinc-200"
                />
                <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1">
                    <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-zinc-800 bg-zinc-900 px-1.5 font-mono text-[10px] font-medium text-zinc-500 shadow-sm opacity-50">
                        <span className="text-xs">⌘</span>K
                    </kbd>
                </div>
            </div>

            {/* Stats */}
            {manifest.stats && (
              <div className="hidden lg:flex items-center gap-3 text-xs text-zinc-500 whitespace-nowrap">
                <span>{manifest.stats.total_files.toLocaleString()} arquivos</span>
                <span className="text-zinc-700">•</span>
                <span>{formatSize(manifest.stats.total_size)}</span>
              </div>
            )}
        </div>
      </header>

      <div className="max-w-[1920px] mx-auto p-6">

      {/* Breadcrumbs */}
      <nav className="flex items-center gap-2 text-sm text-zinc-400 mb-6 bg-zinc-900 p-3 rounded-lg border border-zinc-800 overflow-x-auto scrollbar-hide">
        <button onClick={navigateRoot} className="hover:text-emerald-400 font-medium px-2 py-1 rounded hover:bg-zinc-800 transition-colors flex items-center gap-1">
             <Home className="w-4 h-4" /> Início
        </button>
        {currentPath.map((folder, index) => (
            <React.Fragment key={index}>
                <span className="text-zinc-600"><ChevronRight className="w-4 h-4" /></span>
                <button
                    onClick={() => navigateUp(index)}
                    className={cn(
                        "hover:text-emerald-400 px-2 py-1 rounded hover:bg-zinc-800 transition-colors whitespace-nowrap",
                        index === currentPath.length - 1 && "font-bold text-zinc-100"
                    )}
                >
                    {folder}
                </button>
            </React.Fragment>
        ))}
        <span className="ml-auto text-xs text-zinc-500 whitespace-nowrap pl-4 border-l border-zinc-800 h-4 flex items-center">
            {visibleItems.length} itens {searchQuery && "(filtrado)"}
        </span>
      </nav>

      {/* Content Grid with Virtuoso */}
      <VirtuosoGrid
        useWindowScroll
        totalCount={visibleItems.length}
        overscan={200}
        listClassName="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-4 mb-8"
        itemContent={(index: number) => {
            const item = visibleItems[index];
            if (!item) return null;

            if (item.type === 'directory') {
                return (
                    <div
                        onClick={() => navigateTo(item.name)}
                        className="group cursor-pointer p-4 bg-zinc-900 border border-zinc-800 rounded-xl hover:bg-zinc-800 hover:border-emerald-500/50 transition-all flex flex-col items-center justify-center text-center gap-3 relative select-none h-full"
                    >
                        <div className="text-emerald-500/80 group-hover:text-emerald-400 transition-colors">
                        <Folder className="w-10 h-10" />
                        </div>
                        <span className="font-medium truncate w-full text-sm text-zinc-300 group-hover:text-white">{item.name}</span>
                        <span className="text-xs text-zinc-500">{item.children?.length || 0} itens</span>
                    </div>
                );
            }

            // File Item
            const file = item;
            const isImage = /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(file.name);
            const hasVariants = file.variants && file.variants.length > 1;
            const copyNameId = `name-${file.path}`;
            const copyLinkId = `link-${file.path}`;
            const primaryExt = file.name.includes('.') ? '.' + file.name.split('.').pop()?.toLowerCase() : '';

            return (
                <div
                    className="group relative p-3 bg-zinc-900 border border-zinc-800 rounded-xl hover:bg-zinc-800 hover:border-zinc-700 transition-all flex flex-col items-center gap-2 h-full"
                >
                    {isImage ? (
                        <div
                            className="w-full aspect-square bg-zinc-950 rounded-lg overflow-hidden flex items-center justify-center border border-zinc-800/50 cursor-pointer relative"
                            onClick={() => setPreviewImage({path: file.path, name: file.name, variants: file.variants})}
                        >
                            <img src={`/${file.path}`} alt={file.name} loading="lazy" className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                            <div className="absolute inset-0 bg-black/20 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                <Maximize2 className="text-white w-6 h-6 drop-shadow-md" />
                            </div>
                        </div>
                    ) : (
                        <div className="w-full aspect-square bg-zinc-950 rounded-lg flex items-center justify-center text-zinc-700 border border-zinc-800/50">
                            <FileText className="w-10 h-10" />
                        </div>
                    )}

                    {/* File info: name + badges */}
                    <div className="w-full flex flex-col items-center gap-1 mt-auto">
                        <span className="text-xs font-medium truncate w-full text-center text-zinc-400 group-hover:text-zinc-200" title={file.baseName || file.name}>
                            {file.baseName || file.name}
                        </span>
                        <div className="flex items-center gap-1 flex-wrap justify-center">
                            {/* Format badge(s) */}
                            {hasVariants ? (
                                file.variants!.map(v => (
                                    <span key={v.ext} className={cn("text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border", getExtBadgeColor(v.ext))}>
                                        {v.ext.replace('.', '')}
                                    </span>
                                ))
                            ) : (
                                <span className={cn("text-[9px] font-bold uppercase px-1.5 py-0.5 rounded border", getExtBadgeColor(primaryExt))}>
                                    {primaryExt.replace('.', '') || '?'}
                                </span>
                            )}
                            {/* Size */}
                            {file.size && (
                                <span className="text-[9px] text-zinc-600 ml-1">
                                    {formatSize(file.size)}
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Hover Actions */}
                    <div className="absolute top-2 right-2 flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                        {/* Copy Name */}
                        <button
                            onClick={(e) => copyToClipboard(file.baseName || file.name, copyNameId, e)}
                            className="bg-black/80 hover:bg-emerald-600 text-white p-1.5 rounded-md shadow-lg backdrop-blur-sm transition-colors"
                            title="Copiar Nome"
                        >
                            {copiedState === copyNameId ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>

                        {/* Copy Link — expands with format badges when multiple variants */}
                        {hasVariants ? (
                            <div className="relative" onClick={(e) => e.stopPropagation()}>
                                <button
                                    onClick={(e) => toggleCopyExpand(copyLinkId, e)}
                                    className={cn(
                                        "bg-black/80 hover:bg-emerald-600 text-white p-1.5 rounded-md shadow-lg backdrop-blur-sm transition-colors",
                                        expandedCopyId === copyLinkId && "bg-emerald-600"
                                    )}
                                    title="Copiar Link"
                                >
                                    <LinkIcon className="w-3.5 h-3.5" />
                                </button>
                                {/* Expanded variant picker */}
                                {expandedCopyId === copyLinkId && (
                                    <div className="absolute right-full mr-1 top-0 flex flex-col gap-1 animate-in slide-in-from-right-2 duration-150">
                                        {file.variants!.map(v => {
                                            const variantCopyId = `link-${v.path}`;
                                            const fullUrl = `${CDN_BASE}/${v.path}`;
                                            return (
                                                <button
                                                    key={v.ext}
                                                    onClick={(e) => {
                                                        copyToClipboard(fullUrl, variantCopyId, e);
                                                    }}
                                                    className={cn(
                                                        "flex items-center gap-2 px-2.5 py-1.5 rounded-md shadow-lg backdrop-blur-sm transition-all text-[11px] font-bold uppercase whitespace-nowrap",
                                                        copiedState === variantCopyId
                                                            ? "bg-emerald-600 text-white"
                                                            : `bg-zinc-900/95 border hover:bg-zinc-800 ${getExtBadgeColor(v.ext)}`
                                                    )}
                                                    title={`Copiar link ${v.ext}`}
                                                >
                                                    {copiedState === variantCopyId ? (
                                                        <Check className="w-3 h-3" />
                                                    ) : (
                                                        <LinkIcon className="w-3 h-3" />
                                                    )}
                                                    {v.ext.replace('.', '')}
                                                    <span className="text-[9px] font-normal opacity-60">{formatSize(v.size)}</span>
                                                </button>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        ) : (
                            <button
                                onClick={(e) => copyToClipboard(`${CDN_BASE}/${file.path}`, copyLinkId, e)}
                                className="bg-black/80 hover:bg-emerald-600 text-white p-1.5 rounded-md shadow-lg backdrop-blur-sm transition-colors"
                                title="Copiar Link"
                            >
                                {copiedState === copyLinkId ? <Check className="w-3.5 h-3.5" /> : <LinkIcon className="w-3.5 h-3.5" />}
                            </button>
                        )}

                        {/* Download */}
                        <a
                            href={`/${file.path}`}
                            download
                            className="bg-black/80 hover:bg-emerald-600 text-white p-1.5 rounded-md shadow-lg backdrop-blur-sm transition-colors flex items-center justify-center"
                            title="Baixar"
                            onClick={(e) => e.stopPropagation()}
                        >
                            <Download className="w-3.5 h-3.5" />
                        </a>
                    </div>
                </div>
            );
        }}
    />

      {visibleItems.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-zinc-500 gap-4">
              <Folder className="w-12 h-12 opacity-20" />
              <p>Nenhum item encontrado.</p>
          </div>
      )}


      {/* Image Preview Modal */}
      {previewImage && (
        <div
            className="fixed inset-0 z-50 bg-black/90 backdrop-blur-sm flex items-center justify-center p-4"
            onClick={() => setPreviewImage(null)}
        >
            <button
                className="absolute top-4 right-4 text-zinc-400 hover:text-white transition-colors"
                onClick={() => setPreviewImage(null)}
            >
                <X className="w-8 h-8" />
            </button>
            <div
                className="max-w-full max-h-full relative flex flex-col items-center gap-4"
                onClick={(e) => e.stopPropagation()}
            >
                <img
                    src={`/${previewImage.path}`}
                    alt={previewImage.name}
                    className="max-w-[90vw] max-h-[80vh] object-contain rounded-lg shadow-2xl"
                />
                <div className="flex items-center gap-3 bg-zinc-900/90 px-5 py-3 rounded-xl backdrop-blur-md border border-zinc-800">
                    <span className="text-sm text-zinc-200 font-medium">{previewImage.name}</span>
                    {/* Copy links in modal */}
                    {previewImage.variants && previewImage.variants.length > 0 && (
                        <div className="flex items-center gap-2 ml-3 pl-3 border-l border-zinc-700">
                            {previewImage.variants.map(v => {
                                const modalCopyId = `modal-${v.path}`;
                                return (
                                    <button
                                        key={v.ext}
                                        onClick={(e) => copyToClipboard(`${CDN_BASE}/${v.path}`, modalCopyId, e)}
                                        className={cn(
                                            "flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-bold uppercase transition-colors border",
                                            copiedState === modalCopyId
                                                ? "bg-emerald-600 text-white border-emerald-500"
                                                : `hover:bg-zinc-800 ${getExtBadgeColor(v.ext)}`
                                        )}
                                        title={`Copiar link ${v.ext}`}
                                    >
                                        {copiedState === modalCopyId ? <Check className="w-3 h-3" /> : <LinkIcon className="w-3 h-3" />}
                                        {v.ext.replace('.', '')}
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
      )}
      </div>
    </div>
  );
};
