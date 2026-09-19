const express = require('express');
const router = express.Router();
const browseController = require('../controllers/browseController');

router.get('/browse', browseController.listDir);

module.exports = router;
