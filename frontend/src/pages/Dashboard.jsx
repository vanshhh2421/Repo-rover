import { useState, useEffect, useRef } from "react"
import { Link } from "react-router-dom"
import axios from "axios"
import { Plus, FolderGit2, Search, ArrowRight, Activity, GitBranch, Loader2, X, Trash2, Upload, CheckCircle2, AlertCircle } from "lucide-react"

const ORCHESTRATOR = import.meta.env.VITE_ORCHESTRATOR_URL || "http://localhost:5000"

export default function Dashboard() {
  const [search, setSearch] = useState("")
  const [repos, setRepos] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAdd, setShowAdd] = useState(false)
  const [repoId, setRepoId] = useState("")
  const [repoName, setRepoName] = useState("")
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState("")
  const [error, setError] = useState("")
  const inputRef = useRef(null)

  const fetchRepos = () => {
    setLoading(true)
    axios.get(`${ORCHESTRATOR}/api/repos`).then((res) => setRepos(res.data)).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { fetchRepos() }, [])

  const handleSelectFolder = () => {
    if (!repoId) { setError("Enter a Repo ID first"); return }
    setError("")
    inputRef.current?.click()
  }

  const handleFilesSelected = async (e) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return

    setUploading(true)
    setUploadProgress(`Uploading ${fileList.length} files...`)
    setError("")

    const SKIP_DIRS = new Set(["node_modules", ".git", ".venv", "__pycache__", "dist", "build"])
    const SUPPORTED_EXTS = new Set([".py", ".js", ".jsx", ".ts", ".tsx"])
    const filtered = []
    for (const file of fileList) {
      const parts = file.webkitRelativePath.split("/")
      const fileName = parts.pop()
      if (parts.some((p) => SKIP_DIRS.has(p))) continue
      const ext = "." + (fileName.split(".").pop() || "")
      if (!SUPPORTED_EXTS.has(ext)) continue
      filtered.push(file)
    }
    const formData = new FormData()
    for (const file of filtered) {
      const renamed = new File([file], file.webkitRelativePath, { type: file.type })
      formData.append("files", renamed)
    }
    formData.append("repoId", repoId)
    formData.append("name", repoName || repoId)
    setUploadProgress(`Uploading ${filtered.length} files (skipped ${fileList.length - filtered.length} unwanted)...`)

    try {
      await axios.post(`${ORCHESTRATOR}/api/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (p) => {
          const pct = p.total ? Math.round((p.loaded / p.total) * 100) : 0
          setUploadProgress(`Uploading... ${pct}% (${fileList.length} files)`)
        },
      })
      setShowAdd(false)
      setRepoId("")
      setRepoName("")
      e.target.value = ""
      fetchRepos()
    } catch (err) {
      setError(err.response?.data?.error || err.message)
    } finally {
      setUploading(false)
      setUploadProgress("")
    }
  }

  const handleSync = async (repo) => {
    try {
      await axios.post(`${ORCHESTRATOR}/api/sync`, { repoId: repo.repoId, sourceUrl: repo.sourceUrl })
      fetchRepos()
    } catch (err) {
      const detail = err.response?.data?.worker?.detail || err.response?.data?.details || err.response?.data?.error || err.message
      console.error("[SYNC ERROR]", err.response?.data || err)
      alert(`Sync failed: ${detail}`)
    }
  }

  const handleDelete = async (repo) => {
    if (!confirm(`Delete "${repo.name || repo.repoId}"? This will remove indexed data too.`)) return
    try {
      await axios.delete(`${ORCHESTRATOR}/api/repos/${repo.repoId}`)
      fetchRepos()
    } catch (err) {
      alert(err.response?.data?.error || err.message)
    }
  }

  const filtered = repos.filter((r) => (r.name || "").toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="flex-1 flex flex-col h-full bg-white dark:bg-zinc-950 text-zinc-950 dark:text-zinc-50 overflow-y-auto">
      <header className="px-8 py-6 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Workspaces</h1>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">Manage and query your indexed repositories.</p>
          </div>
          <button onClick={() => setShowAdd(true)} className="inline-flex items-center justify-center rounded-md text-sm font-medium h-9 px-4 py-2 bg-zinc-900 dark:bg-zinc-50 text-zinc-50 dark:text-zinc-900 shadow hover:bg-zinc-900/90 dark:hover:bg-zinc-50/90">
            <Plus className="w-4 h-4 mr-2" /> Add Repository
          </button>
        </div>
      </header>

      <div className="p-8">
        <div className="relative mb-6">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500 dark:text-zinc-400" />
          <input
            type="text"
            placeholder="Search repositories..."
            className="flex h-9 w-full md:w-[300px] rounded-md border border-zinc-200 dark:border-zinc-800 bg-transparent px-3 py-1 text-sm shadow-sm pl-9 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-zinc-950 dark:focus-visible:ring-zinc-300"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="grid gap-4">
          {loading ? (
            <div className="flex items-center gap-2 text-zinc-500 text-sm"><Loader2 className="w-4 h-4 animate-spin" /> Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="text-zinc-500 text-sm">No repositories found. Add one to get started.</div>
          ) : (
            filtered.map((repo) => (
              <div key={repo._id || repo.repoId} className="group flex flex-col sm:flex-row sm:items-center justify-between p-6 rounded-lg border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-sm hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-full bg-zinc-100 dark:bg-zinc-900 flex items-center justify-center">
                    <FolderGit2 className="h-5 w-5 text-zinc-900 dark:text-zinc-100" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg flex items-center gap-2">
                      {repo.name || repo.repoId}
                      <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold border-transparent ${
                        repo.status === "indexed" ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400" :
                        repo.status === "indexing" ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400" :
                        repo.status === "error" ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400" :
                        "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"
                      }`}>
                        {repo.status || "not_indexed"}
                      </span>
                    </h3>
                    <div className="flex items-center text-sm text-zinc-500 dark:text-zinc-400 mt-1 gap-4">
                      <span className="flex items-center gap-1"><GitBranch className="h-3.5 w-3.5" />{repo.branch || "main"}</span>
                      <span className="flex items-center gap-1"><Activity className="h-3.5 w-3.5" />{repo.lastSyncAt ? new Date(repo.lastSyncAt).toLocaleDateString() : "never"}</span>
                    </div>
                  </div>
                </div>
                <div className="mt-4 sm:mt-0 flex items-center gap-3">
                  <div className="flex items-center gap-4 text-sm text-zinc-500 dark:text-zinc-400 mr-4">
                    <div className="flex flex-col items-end"><span className="font-medium text-zinc-900 dark:text-zinc-100">{repo.nodeCount ?? 0}</span><span className="text-xs">Nodes</span></div>
                  </div>
                  <button onClick={() => handleDelete(repo)} className="inline-flex items-center justify-center rounded-md text-sm font-medium h-9 px-3 py-2 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400 bg-transparent shadow-sm hover:bg-red-50 dark:hover:bg-red-950 opacity-0 group-hover:opacity-100 transition-opacity" title="Delete">
                    <Trash2 className="w-4 h-4" />
                  </button>
                  {repo.status !== "indexed" && (
                    <button onClick={() => handleSync(repo)} className="inline-flex items-center justify-center rounded-md text-sm font-medium h-9 px-4 py-2 border border-zinc-200 dark:border-zinc-800 bg-transparent shadow-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors">
                      Sync
                    </button>
                  )}
                  <Link to={`/repo/${repo.repoId}`} className="inline-flex items-center justify-center rounded-md text-sm font-medium h-9 px-4 py-2 border border-zinc-200 dark:border-zinc-800 bg-transparent shadow-sm hover:bg-zinc-100 dark:hover:bg-zinc-800 opacity-0 group-hover:opacity-100 transition-opacity">
                    Explore <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {showAdd && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => { if (!uploading) { setShowAdd(false); setError("") } }}>
          <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 w-full max-w-md border border-zinc-200 dark:border-zinc-800 shadow-xl" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Add Repository</h2>
              <button onClick={() => { setShowAdd(false); setError("") }} className="p-1 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500"><X className="w-5 h-5" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Repo ID</label>
                <input type="text" value={repoId} onChange={(e) => setRepoId(e.target.value)} placeholder="e.g. my-app" className="w-full rounded-md border border-zinc-200 dark:border-zinc-800 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-600" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Display Name (optional)</label>
                <input type="text" value={repoName} onChange={(e) => setRepoName(e.target.value)} placeholder="e.g. My Application" className="w-full rounded-md border border-zinc-200 dark:border-zinc-800 bg-transparent px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-600" />
              </div>
              <div className="border-t border-zinc-200 dark:border-zinc-800 pt-4">
                <p className="text-sm text-zinc-500 dark:text-zinc-400 mb-3">Select a folder from your computer to upload and index.</p>
                <button
                  onClick={handleSelectFolder}
                  disabled={uploading}
                  className="w-full inline-flex items-center justify-center rounded-md text-sm font-medium h-10 px-4 py-2 bg-blue-600 text-white shadow hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {uploading ? (
                    <><Loader2 className="w-4 h-4 animate-spin mr-2" /> {uploadProgress || "Uploading..."}</>
                  ) : (
                    <><Upload className="w-4 h-4 mr-2" /> Select Folder & Upload</>
                  )}
                </button>
                <input ref={inputRef} type="file" webkitdirectory="" multiple className="hidden" onChange={handleFilesSelected} />
              </div>
              {error && (
                <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950 rounded-md px-3 py-2">
                  <AlertCircle className="w-4 h-4 shrink-0" /> {error}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
