const express = require('express');
const router = express.Router();
const queryController = require('../controllers/queryController');

router.post('/query', queryController.queryRepo);
router.get('/graph/:repoId', queryController.getGraph);

module.exports = router;
