const express = require('express');
const router = express.Router();
const repoController = require('../controllers/repoController');

router.post('/repos', repoController.createRepo);
router.get('/repos', repoController.listRepos);
router.get('/repos/:id', repoController.getRepo);
router.delete('/repos/:id', repoController.deleteRepo);

module.exports = router;
