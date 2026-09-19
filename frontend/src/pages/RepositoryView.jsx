import { useState, useEffect, useCallback, useRef } from "react"
import { useParams } from "react-router-dom"
import ForceGraph2D from "react-force-graph-2d"
import axios from "axios"
import { MessageSquare, Maximize2, Minimize2, Send, Loader2 } from "lucide-react"
import { useTheme } from "../components/ThemeProvider"

const API = import.meta.env.VITE_ORCHESTRATOR_URL || "http://localhost:5000"

export default function RepositoryView() {
  const { repoId } = useParams()
  const { theme } = useTheme()

  const [messages, setMessages] = useState([
    { role: "assistant", content: `Hi! Ask me anything about ${repoId}.` },
  ])
  const [input, setInput] = useState("")
  const [chatExpanded, setChatExpanded] = useState(false)
  const [queryLoading, setQueryLoading] = useState(false)

  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [graphLoading, setGraphLoading] = useState(true)

  const fgRef = useRef()
  const graphContainerRef = useRef()
  const [graphSize, setGraphSize] = useState({ width: 0, height: 0 })

  useEffect(() => {
    const el = graphContainerRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setGraphSize({ width: entry.contentRect.width, height: entry.contentRect.height })
      }
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    axios.get(`${API}/api/graph/${repoId}`).then((res) => setGraphData(res.data)).catch((err) => console.error("[GRAPH ERROR]", err.response?.data || err.message)).finally(() => setGraphLoading(false))
  }, [repoId])

  const handleSend = useCallback(async () => {
    if (!input.trim() || queryLoading) return
    const userMsg = { role: "user", content: input }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setQueryLoading(true)
    try {
      const res = await axios.post(`${API}/api/query`, { repoId, question: userMsg.content })
      setMessages((prev) => [...prev, { role: "assistant", content: res.data.answer }])
    } catch (err) {
      const detail = err.response?.data?.worker?.detail || err.response?.data?.details || err.response?.data?.error || err.message
      console.error("[QUERY ERROR]", err.response?.data || err)
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${detail}` }])
    } finally {
      setQueryLoading(false)
    }
  }, [input, queryLoading, repoId])

  const colors = {
    bg: theme === "dark" ? "#09090b" : "#ffffff",
    link: theme === "dark" ? "#27272a" : "#e4e4e7",
    file: theme === "dark" ? "#3b82f6" : "#2563eb",
    func: theme === "dark" ? "#10b981" : "#059669",
    cls: theme === "dark" ? "#f59e0b" : "#d97706",
  }

  const nodeColor = (n) => {
    if (n.labels?.includes("File")) return colors.file
    if (n.labels?.includes("Function")) return colors.func
    if (n.labels?.includes("Class")) return colors.cls
    return colors.link
  }

  const handleNodeClick = useCallback((node) => {
    setInput(`Explain ${node.qualified_name || node.name || node.id}`)
  }, [])

  const nodeCanvasObject = useCallback((node, ctx, globalScale) => {
    if (globalScale < 3) return
    const label = node.name || node.qualified_name || node.id
    const fontSize = 12 / globalScale
    ctx.font = `${fontSize}px Sans-Serif`
    const textWidth = ctx.measureText(label).width
    const bckgDimensions = [textWidth, fontSize].map((n) => n + fontSize * 0.2)

    ctx.fillStyle = colors.bg
    ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, bckgDimensions[0], bckgDimensions[1])

    ctx.textAlign = "center"
    ctx.textBaseline = "middle"
    ctx.fillStyle = nodeColor(node)
    ctx.fillText(label, node.x, node.y)
  }, [colors])

  const nodeCanvasObjectMode = useCallback(() => "replace", [])

  return (
    <div className="flex h-full w-full bg-white dark:bg-zinc-950 text-zinc-950 dark:text-zinc-50 relative overflow-hidden">
      <div ref={graphContainerRef} className={`relative flex-1 min-w-0 h-full overflow-hidden transition-all duration-300 z-0 ${chatExpanded ? "hidden" : "block"}`}>
        {graphLoading ? (
          <div className="flex items-center justify-center h-full text-zinc-500">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
        ) : graphData.nodes.length === 0 ? (
          <div className="flex items-center justify-center h-full text-zinc-500 flex-col">
            <p>No graph data found. Sync a repo first.</p>
          </div>
        ) : graphSize.width > 0 && graphSize.height > 0 ? (
          <ForceGraph2D
            ref={fgRef}
            width={graphSize.width}
            height={graphSize.height}
            graphData={graphData}
            backgroundColor={colors.bg}
            linkColor={() => colors.link}
            nodeColor={nodeColor}
            nodeLabel={(n) => n.qualified_name || n.name || n.id}
            nodeCanvasObject={nodeCanvasObject}
            nodeCanvasObjectMode={nodeCanvasObjectMode}
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            onNodeClick={handleNodeClick}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-zinc-500">
            <Loader2 className="w-8 h-8 animate-spin" />
          </div>
        )}
      </div>

      <div className={`relative z-10 border-l border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 flex flex-col transition-all duration-300 ${chatExpanded ? "w-full max-w-4xl mx-auto border-l-0" : "w-[400px]"}`}>
        <div className="h-14 border-b border-zinc-200 dark:border-zinc-800 flex items-center justify-between px-4">
          <h3 className="font-medium flex items-center gap-2">
            <MessageSquare className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            Agent
          </h3>
          <button onClick={() => setChatExpanded(!chatExpanded)} className="p-1.5 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500 transition-colors">
            {chatExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-lg p-3 text-sm ${msg.role === "user" ? "bg-blue-600 dark:bg-blue-500 text-white" : "bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100"}`}>
                {msg.content}
              </div>
            </div>
          ))}
          {queryLoading && (
            <div className="flex justify-start">
              <div className="max-w-[85%] rounded-lg p-3 text-sm bg-zinc-100 dark:bg-zinc-800 text-zinc-500 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> Thinking...
              </div>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-zinc-200 dark:border-zinc-800">
          <div className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
              placeholder="Ask about this repo..."
              className="w-full bg-white dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-md px-4 py-2.5 pr-12 text-sm focus:outline-none focus:ring-1 focus:ring-blue-600 shadow-sm"
            />
            <button onClick={handleSend} disabled={!input.trim() || queryLoading} className="absolute right-2 p-1.5 rounded-md text-zinc-500 hover:text-blue-600 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors disabled:opacity-50">
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
