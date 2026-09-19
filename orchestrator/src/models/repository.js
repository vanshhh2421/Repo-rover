const mongoose = require('mongoose');

const repositorySchema = new mongoose.Schema({
  repoId: { type: String, required: true, unique: true, index: true },
  name: { type: String, required: true },
  sourceUrl: { type: String, required: true },
  branch: { type: String, default: 'main' },
  status: {
    type: String,
    enum: ['not_indexed', 'indexing', 'indexed', 'error'],
    default: 'not_indexed',
  },
  lastSyncAt: { type: Date, default: null },
  nodeCount: { type: Number, default: 0 },
  edgeCount: { type: Number, default: 0 },
  createdAt: { type: Date, default: Date.now },
});

module.exports = mongoose.model('Repository', repositorySchema);
