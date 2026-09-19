const fs = require('fs');
const path = require('path');

exports.listDir = async (req, res) => {
  try {
    const dirPath = req.query.path || (process.platform === 'win32' ? 'C:/' : '/');
    const resolved = path.resolve(dirPath);
    if (!fs.existsSync(resolved)) {
      return res.status(404).json({ error: 'Path not found', path: dirPath });
    }
    const entries = fs.readdirSync(resolved, { withFileTypes: true });
    const dirs = entries.filter(e => e.isDirectory()).map(e => ({ name: e.name, path: path.join(resolved, e.name).replace(/\\/g, '/') }));
    const files = entries.filter(e => e.isFile()).map(e => ({ name: e.name, path: path.join(resolved, e.name).replace(/\\/g, '/') }));
    res.json({ current: resolved.replace(/\\/g, '/'), parent: path.dirname(resolved).replace(/\\/g, '/'), dirs, files });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
};
