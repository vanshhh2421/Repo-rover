const express = require('express');
const multer = require('multer');
const router = express.Router();
const uploadController = require('../controllers/uploadController');
const os = require('os');

const upload = multer({ dest: os.tmpdir() + '/reporover-uploads' });

router.post('/upload', upload.array('files'), uploadController.uploadRepo);

module.exports = router;
