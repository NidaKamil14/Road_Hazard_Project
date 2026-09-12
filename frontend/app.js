document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const headerUpload = document.getElementById('header-upload');
  const headerResults = document.getElementById('header-results');
  const hazardsSpec = document.getElementById('hazards-spec');

  const viewEmpty = document.getElementById('view-empty');
  const viewSelected = document.getElementById('view-selected');
  const viewAnalyzing = document.getElementById('view-analyzing');
  const viewError = document.getElementById('view-error');
  
  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-upload-input');
  
  const imagePreview = document.getElementById('image-preview');
  const imagePreviewAnalyzing = document.getElementById('image-preview-analyzing');
  const fileNameDisplay = document.getElementById('file-name');
  const fileSizeDisplay = document.getElementById('file-size');
  
  const btnChooseFile = document.querySelector('.btn-choose');
  const btnDetectDisabled = document.getElementById('btn-detect-disabled');
  const btnDetectAction = document.getElementById('btn-detect-action');
  const btnChooseDifferent = document.getElementById('btn-choose-different');
  const btnAnalyseAnother = document.getElementById('btn-analyse-another');
  const btnDownloadResult = document.getElementById('btn-download-result');

  // Modal Elements
  const btnHowItWorks = document.getElementById('btn-how-it-works');
  const modalHowItWorks = document.getElementById('modal-how-it-works');
  const btnCloseModal = document.getElementById('btn-close-modal');

  // Results Elements
  const imageResult = document.getElementById('image-result');
  const resultFileName = document.getElementById('result-file-name');
  const totalDetectionsText = document.getElementById('total-detections-text');
  const summaryTotal = document.getElementById('summary-total');
  const categoryCountsContainer = document.getElementById('category-counts-container');
  const detectionDetailsList = document.getElementById('detection-details-list');

  let currentFile = null;

  // Mock Data for Results
  const MOCK_DETECTIONS = [
    { classId: 'Potholes', displayName: 'Pothole', conf: '92%', color: 'orange' },
    { classId: 'Road Cracks', displayName: 'Road Crack', conf: '87%', color: 'yellow' },
    { classId: 'Construction Barriers', displayName: 'Construction Barrier', conf: '81%', color: 'orange' }
  ];

  const HAZARD_CATEGORIES = [
    'Potholes',
    'Road Cracks',
    'Waterlogging',
    'Construction Barriers'
  ];

  // --- Modal Logic ---
  const openModal = () => {
    modalHowItWorks.classList.remove('hidden');
    btnCloseModal.focus();
  };

  const closeModal = () => {
    modalHowItWorks.classList.add('hidden');
    btnHowItWorks.focus();
  };

  btnHowItWorks.addEventListener('click', openModal);
  btnCloseModal.addEventListener('click', closeModal);

  modalHowItWorks.addEventListener('click', (e) => {
    if (e.target === modalHowItWorks) closeModal();
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modalHowItWorks.classList.contains('hidden')) {
      closeModal();
    }
  });

  // --- File Upload Logic ---
  const isValidFileType = (file) => {
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
    return validTypes.includes(file.type);
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const handleFileSelect = (file) => {
    viewError.classList.add('hidden');

    if (!file) return;

    if (!isValidFileType(file)) {
      viewError.classList.remove('hidden');
      return;
    }

    currentFile = file;

    // Create object URL for preview
    const objectUrl = URL.createObjectURL(file);
    imagePreview.src = objectUrl;
    imagePreviewAnalyzing.src = objectUrl;
    imageResult.src = objectUrl; // Use the same image for the mock result

    fileNameDisplay.textContent = file.name;
    resultFileName.textContent = file.name.toUpperCase();
    fileSizeDisplay.textContent = formatFileSize(file.size);

    // Switch State
    viewEmpty.classList.remove('active');
    viewEmpty.classList.add('hidden');
    viewSelected.classList.remove('hidden');
    viewSelected.classList.add('active');
  };

  // Click to upload
  btnChooseFile.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropZone.addEventListener('click', () => {
    fileInput.click();
  });

  dropZone.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInput.click();
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileSelect(e.target.files[0]);
    }
  });

  // Drag and drop
  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });

  dropZone.addEventListener('dragleave', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length > 0) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  });

  // --- State Navigation ---
  btnChooseDifferent.addEventListener('click', () => {
    // Reset file input
    fileInput.value = '';
    currentFile = null;
    imagePreview.src = '';
    imagePreviewAnalyzing.src = '';
    imageResult.src = '';
    viewError.classList.add('hidden');
    
    // Switch state
    viewSelected.classList.remove('active');
    viewSelected.classList.add('hidden');
    viewEmpty.classList.remove('hidden');
    viewEmpty.classList.add('active');
  });

  // Detect Hazards
  btnDetectAction.addEventListener('click', () => {
    // Switch to analyzing state
    viewSelected.classList.remove('active');
    viewSelected.classList.add('hidden');
    viewAnalyzing.classList.remove('hidden');
    viewAnalyzing.classList.add('active');

    // Simulate API delay
    setTimeout(() => {
      showResults();
    }, 2000);
  });

  // Show Results
  const showResults = () => {
    headerUpload.classList.add('hidden');
    hazardsSpec.classList.add('hidden');
    
    headerResults.classList.remove('hidden');

    populateResultsData();
  };

  const populateResultsData = () => {
    const totalDetections = MOCK_DETECTIONS.length;
    totalDetectionsText.textContent = totalDetections;
    summaryTotal.textContent = totalDetections;

    // Calculate Category Counts
    const counts = {};
    HAZARD_CATEGORIES.forEach(cat => counts[cat] = 0);
    MOCK_DETECTIONS.forEach(det => {
      if (counts[det.classId] !== undefined) {
        counts[det.classId]++;
      }
    });

    categoryCountsContainer.innerHTML = '';
    HAZARD_CATEGORIES.forEach(cat => {
      const value = counts[cat];
      const isZero = value === 0;
      const row = document.createElement('div');
      row.className = 'count-row';
      row.innerHTML = `
        <span class="count-name ${isZero ? 'zero' : ''}">${cat}</span>
        <span class="count-val ${isZero ? 'zero' : ''}">${value}</span>
      `;
      categoryCountsContainer.appendChild(row);
    });

    // Populate Details List
    detectionDetailsList.innerHTML = '';
    MOCK_DETECTIONS.forEach(detail => {
      const item = document.createElement('div');
      item.className = 'detail-item';
      item.innerHTML = `
        <div class="detail-left">
          <span class="indicator-dot ${detail.color}"></span>
          <div class="detail-info">
            <span class="detail-title">${detail.displayName}</span>
          </div>
        </div>
        <div class="detail-right">
          <span class="detail-conf">${detail.conf}</span>
        </div>
      `;
      detectionDetailsList.appendChild(item);
    });
  };

  // Analyse Another Image
  btnAnalyseAnother.addEventListener('click', () => {
    headerResults.classList.add('hidden');
    headerUpload.classList.remove('hidden');
    hazardsSpec.classList.remove('hidden');
    
    fileInput.value = '';
    currentFile = null;
    imagePreview.src = '';
    imagePreviewAnalyzing.src = '';
    imageResult.src = '';
    
    viewError.classList.add('hidden');

    viewAnalyzing.classList.remove('active');
    viewAnalyzing.classList.add('hidden');
    viewSelected.classList.remove('active');
    viewSelected.classList.add('hidden');
    viewEmpty.classList.remove('hidden');
    viewEmpty.classList.add('active');
  });

  // Download Result
  btnDownloadResult.addEventListener('click', () => {
    if (imageResult.src) {
      const a = document.createElement('a');
      a.href = imageResult.src;
      a.download = `detection_result_${currentFile ? currentFile.name : 'image'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    }
  });
});
