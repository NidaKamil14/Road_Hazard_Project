const CONFIG = {
  USE_MOCK_API: true,
  API_BASE_URL: "http://localhost:5000",
  DETECT_ENDPOINT: "/api/detect",
  REQUEST_TIMEOUT_MS: 30000
};

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const headerUpload = document.getElementById('header-upload');
  const headerResults = document.getElementById('header-results');
  const hazardsSpec = document.getElementById('hazards-spec');

  const viewEmpty = document.getElementById('view-empty');
  const viewSelected = document.getElementById('view-selected');
  const viewAnalyzing = document.getElementById('view-analyzing');
  const viewApiError = document.getElementById('view-api-error');
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
  const btnErrorChooseDifferent = document.getElementById('btn-error-choose-different');
  const btnRetry = document.getElementById('btn-retry');
  const btnAnalyseAnother = document.getElementById('btn-analyse-another');
  const btnDownloadResult = document.getElementById('btn-download-result');

  const demoModeNotice = document.getElementById('demo-mode-notice');
  const resultsMainHeading = document.getElementById('results-main-heading');
  const resultsEditorialText = document.getElementById('results-editorial-text');
  const hazardSummaryCard = document.querySelector('.hazard-summary-card');
  const resultsGrid = document.querySelector('.results-grid');

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
  const resetToEmptyState = () => {
    fileInput.value = '';
    currentFile = null;
    imagePreview.src = '';
    imagePreviewAnalyzing.src = '';
    imageResult.src = '';
    viewError.classList.add('hidden');
    
    viewSelected.classList.remove('active');
    viewSelected.classList.add('hidden');
    viewAnalyzing.classList.remove('active');
    viewAnalyzing.classList.add('hidden');
    viewApiError.classList.remove('active');
    viewApiError.classList.add('hidden');
    
    viewEmpty.classList.remove('hidden');
    viewEmpty.classList.add('active');
  };

  btnChooseDifferent.addEventListener('click', resetToEmptyState);
  btnErrorChooseDifferent.addEventListener('click', resetToEmptyState);

  // Detect Hazards
  const performDetection = async () => {
    // Switch to analyzing state
    viewSelected.classList.remove('active');
    viewSelected.classList.add('hidden');
    viewApiError.classList.remove('active');
    viewApiError.classList.add('hidden');
    viewAnalyzing.classList.remove('hidden');
    viewAnalyzing.classList.add('active');

    try {
      const responseData = await detectHazards(currentFile);
      
      // Success
      showResults(responseData.detections);

    } catch (err) {
      // Error State
      viewAnalyzing.classList.remove('active');
      viewAnalyzing.classList.add('hidden');
      
      const errorMessage = document.getElementById('api-error-message');
      if (err.name === 'AbortError') {
        errorMessage.textContent = 'Request timed out. The server took too long to respond.';
      } else {
        errorMessage.textContent = err.message || 'Unable to process the uploaded image.';
      }
      
      viewApiError.classList.remove('hidden');
      viewApiError.classList.add('active');
    }
  };

  btnDetectAction.addEventListener('click', performDetection);
  btnRetry.addEventListener('click', performDetection);

  const detectHazards = async (file) => {
    if (CONFIG.USE_MOCK_API) {
      return new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            success: true,
            detections: MOCK_DETECTIONS
          });
        }, 2000);
      });
    } else {
      const formData = new FormData();
      formData.append('image', file);

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT_MS);

      try {
        const response = await fetch(CONFIG.API_BASE_URL + CONFIG.DETECT_ENDPOINT, {
          method: 'POST',
          body: formData,
          signal: controller.signal
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error('Backend unavailable or returned an error.');
        }

        const data = await response.json();
        if (!data.success) {
          throw new Error(data.error || 'Invalid server response.');
        }

        return data;
      } catch (err) {
        clearTimeout(timeoutId);
        throw err;
      }
    }
  };

  // Show Results
  const showResults = (detections) => {
    viewAnalyzing.classList.remove('active');
    viewAnalyzing.classList.add('hidden');

    headerUpload.classList.add('hidden');
    hazardsSpec.classList.add('hidden');
    
    headerResults.classList.remove('hidden');

    if (!CONFIG.USE_MOCK_API && demoModeNotice) {
      demoModeNotice.classList.add('hidden');
    }

    populateResultsData(detections);
  };

  const populateResultsData = (detections = []) => {
    const totalDetections = detections.length;
    totalDetectionsText.textContent = totalDetections;
    summaryTotal.textContent = totalDetections;

    if (totalDetections === 0) {
      resultsMainHeading.innerHTML = `No <span class="highlight-underline">road hazards</span> were detected in this image.`;
      resultsEditorialText.style.display = 'none';
      if (hazardSummaryCard) hazardSummaryCard.classList.add('hidden');
      if (resultsGrid) resultsGrid.classList.add('full-width');
    } else {
      resultsMainHeading.innerHTML = `<span id="total-detections-text">${totalDetections}</span> <span class="highlight-underline">road hazards</span> detected.`;
      resultsEditorialText.style.display = 'block';
      if (hazardSummaryCard) hazardSummaryCard.classList.remove('hidden');
      if (resultsGrid) resultsGrid.classList.remove('full-width');
    }

    // Calculate Category Counts
    const counts = {};
    HAZARD_CATEGORIES.forEach(cat => counts[cat] = 0);
    detections.forEach(det => {
      // Map API format if necessary or use mock format
      const cat = det.classId || det.class_name;
      if (cat === 'Pothole') counts['Potholes']++;
      else if (cat === 'Road Crack') counts['Road Cracks']++;
      else if (counts[cat] !== undefined) counts[cat]++;
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
    detections.forEach(detail => {
      // Handle both mock format and future API format
      const title = detail.displayName || detail.class_name;
      let conf = detail.conf;
      if (!conf && detail.confidence !== undefined) {
        conf = Math.round(detail.confidence * 100) + '%';
      }
      const color = detail.color || (title === 'Road Crack' ? 'yellow' : 'orange');

      const item = document.createElement('div');
      item.className = 'detail-item';
      item.innerHTML = `
        <div class="detail-left">
          <span class="indicator-dot ${color}"></span>
          <div class="detail-info">
            <span class="detail-title">${title}</span>
          </div>
        </div>
        <div class="detail-right">
          <span class="detail-conf">${conf}</span>
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
