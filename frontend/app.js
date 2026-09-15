const CONFIG = {
  API_BASE_URL: "http://127.0.0.1:5000",
  DETECT_ENDPOINT: "/detect/image?conf=0.25&iou=0.45",
  REQUEST_TIMEOUT_MS: 30000
};

// Maps raw backend class_name values to display labels
const CLASS_NAME_MAP = {
  pothole:               "Pothole",
  road_crack:            "Road Crack",
  waterlogging:          "Waterlogging",
  construction_barrier:  "Construction Barrier"
};

// Maps display names to category keys used in the summary counts
const DISPLAY_TO_CATEGORY = {
  "Pothole":              "Potholes",
  "Road Crack":           "Road Cracks",
  "Waterlogging":         "Waterlogging",
  "Construction Barrier": "Construction Barriers"
};

// Ordered list of category display keys — must match DISPLAY_TO_CATEGORY values
const HAZARD_CATEGORIES = [
  "Potholes",
  "Road Cracks",
  "Waterlogging",
  "Construction Barriers"
];

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
  let isProcessing = false;
  // Track the local preview object URL so we can revoke it when done
  let currentPreviewUrl = null;

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

  const revokePreviewUrl = () => {
    if (currentPreviewUrl) {
      URL.revokeObjectURL(currentPreviewUrl);
      currentPreviewUrl = null;
    }
  };

  const handleFileSelect = (file) => {
    viewError.classList.add('hidden');

    if (!file) return;

    if (!isValidFileType(file)) {
      viewError.classList.remove('hidden');
      return;
    }

    // Revoke any previous object URL before creating a new one
    revokePreviewUrl();

    currentFile = file;

    // Create object URL for the upload preview only
    currentPreviewUrl = URL.createObjectURL(file);
    imagePreview.src = currentPreviewUrl;
    imagePreviewAnalyzing.src = currentPreviewUrl;
    // imageResult will be set to the backend annotated image after analysis

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
    revokePreviewUrl();
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

    isProcessing = false;
  };

  btnChooseDifferent.addEventListener('click', resetToEmptyState);
  btnErrorChooseDifferent.addEventListener('click', resetToEmptyState);

  // Detect Hazards
  const performDetection = async () => {
    // Prevent duplicate submissions while a request is running
    if (isProcessing) return;
    isProcessing = true;

    // Switch to analyzing state
    viewSelected.classList.remove('active');
    viewSelected.classList.add('hidden');
    viewApiError.classList.remove('active');
    viewApiError.classList.add('hidden');
    viewAnalyzing.classList.remove('hidden');
    viewAnalyzing.classList.add('active');

    try {
      const responseData = await detectHazards(currentFile);

      // Revoke the local preview URL — the annotated image from the backend
      // is now the authoritative visual output.
      revokePreviewUrl();

      showResults(responseData);

    } catch (err) {
      // Restore processing flag and show error
      isProcessing = false;

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

  /**
   * Sends the image file to the real FastAPI YOLO backend.
   * Returns the parsed DetectionResponse on success.
   * Throws a descriptive Error on any failure — never falls back to mock data.
   */
  const detectHazards = async (file) => {
    const formData = new FormData();
    // Field name MUST be "file" to match the FastAPI UploadFile parameter
    formData.append('file', file);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT_MS);

    let response;
    try {
      response = await fetch(CONFIG.API_BASE_URL + CONFIG.DETECT_ENDPOINT, {
        method: 'POST',
        body: formData,
        // Do NOT set Content-Type — the browser must add the multipart boundary
        signal: controller.signal
      });
    } catch (err) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') throw err;
      throw new Error(
        'Cannot reach the detection server. Please ensure the backend is running on http://127.0.0.1:5000.'
      );
    }

    clearTimeout(timeoutId);

    if (!response.ok) {
      let detail = `Server returned ${response.status}`;
      try {
        const errJson = await response.json();
        if (errJson.detail) detail = errJson.detail;
      } catch (_) { /* ignore JSON parse error on error body */ }
      throw new Error(detail);
    }

    let data;
    try {
      data = await response.json();
    } catch (_) {
      throw new Error('The server returned an invalid response. Please try again.');
    }

    if (!data.success) {
      throw new Error(data.error || 'The server indicated the detection did not succeed.');
    }

    return data;
  };

  /**
   * Resolves the annotated_image_url from the backend response.
   * Prefixes relative URLs with the API base URL.
   */
  const resolveAnnotatedImageUrl = (rawUrl) => {
    if (!rawUrl) return null;
    if (rawUrl.startsWith('http://') || rawUrl.startsWith('https://')) {
      return rawUrl;
    }
    const normalised = rawUrl.startsWith('/') ? rawUrl : '/' + rawUrl;
    return CONFIG.API_BASE_URL + normalised;
  };

  /**
   * Transitions to the results view using the real backend DetectionResponse.
   */
  const showResults = (responseData) => {
    viewAnalyzing.classList.remove('active');
    viewAnalyzing.classList.add('hidden');

    headerUpload.classList.add('hidden');
    hazardsSpec.classList.add('hidden');
    headerResults.classList.remove('hidden');

    // Always hide the demo-mode notice — results are real
    if (demoModeNotice) {
      demoModeNotice.classList.add('hidden');
    }

    // Display the backend annotated image (already contains YOLO bounding boxes)
    const annotatedUrl = resolveAnnotatedImageUrl(responseData.annotated_image_url);
    if (annotatedUrl) {
      imageResult.src = annotatedUrl;
      imageResult.onerror = () => {
        imageResult.alt = 'Annotated image could not be loaded from the server.';
      };
    } else {
      imageResult.alt = 'No annotated image was returned by the server.';
    }

    populateResultsData(responseData);
  };

  /**
   * Populates counts and detail cards from the real DetectionResponse object.
   */
  const populateResultsData = (responseData) => {
    const detections = responseData.detections || [];
    const totalDetections = responseData.total_detections;

    totalDetectionsText.textContent = totalDetections;
    summaryTotal.textContent = totalDetections;

    if (totalDetections === 0) {
      // Update heading for zero-detection case without re-creating the span
      resultsMainHeading.textContent = '';
      const noText = document.createTextNode('No ');
      const underlineSpan = document.createElement('span');
      underlineSpan.className = 'highlight-underline';
      underlineSpan.textContent = 'road hazards';
      resultsMainHeading.appendChild(noText);
      resultsMainHeading.appendChild(underlineSpan);
      resultsMainHeading.appendChild(document.createTextNode(' were detected in this image.'));
      resultsEditorialText.style.display = 'none';
      if (hazardSummaryCard) hazardSummaryCard.classList.add('hidden');
      if (resultsGrid) resultsGrid.classList.add('full-width');
    } else {
      // Update the count in the existing span to avoid re-creating DOM and orphaning the ref
      totalDetectionsText.textContent = totalDetections;
      resultsEditorialText.style.display = 'block';
      if (hazardSummaryCard) hazardSummaryCard.classList.remove('hidden');
      if (resultsGrid) resultsGrid.classList.remove('full-width');
    }

    // Build category counts from the real detections array
    const counts = {};
    HAZARD_CATEGORIES.forEach(cat => counts[cat] = 0);
    detections.forEach(det => {
      // Map raw backend class_name ("pothole") → display name ("Pothole") → category key ("Potholes")
      const displayName = CLASS_NAME_MAP[det.class_name] || det.class_name;
      const categoryKey = DISPLAY_TO_CATEGORY[displayName];
      if (categoryKey !== undefined) {
        counts[categoryKey]++;
      }
    });

    categoryCountsContainer.innerHTML = '';
    HAZARD_CATEGORIES.forEach(cat => {
      const value = counts[cat];
      const isZero = value === 0;
      const row = document.createElement('div');
      row.className = 'count-row';
      // Use textContent for safe insertion — no innerHTML with data values
      const nameSpan = document.createElement('span');
      nameSpan.className = 'count-name' + (isZero ? ' zero' : '');
      nameSpan.textContent = cat;
      const valSpan = document.createElement('span');
      valSpan.className = 'count-val' + (isZero ? ' zero' : '');
      valSpan.textContent = value;
      row.appendChild(nameSpan);
      row.appendChild(valSpan);
      categoryCountsContainer.appendChild(row);
    });

    // Populate detection detail cards from the real detections
    detectionDetailsList.innerHTML = '';
    detections.forEach(det => {
      const displayName = CLASS_NAME_MAP[det.class_name] || det.class_name;
      // Convert decimal confidence to percentage, e.g. 0.8179 → "81.8%"
      const confidencePct = (det.confidence * 100).toFixed(1) + '%';
      // Colour indicator: yellow for Road Crack, orange for everything else
      const color = displayName === 'Road Crack' ? 'yellow' : 'orange';

      const item = document.createElement('div');
      item.className = 'detail-item';

      const leftDiv = document.createElement('div');
      leftDiv.className = 'detail-left';

      const dot = document.createElement('span');
      dot.className = 'indicator-dot ' + color;

      const infoDiv = document.createElement('div');
      infoDiv.className = 'detail-info';

      const titleSpan = document.createElement('span');
      titleSpan.className = 'detail-title';
      titleSpan.textContent = displayName;

      infoDiv.appendChild(titleSpan);
      leftDiv.appendChild(dot);
      leftDiv.appendChild(infoDiv);

      const rightDiv = document.createElement('div');
      rightDiv.className = 'detail-right';

      const confSpan = document.createElement('span');
      confSpan.className = 'detail-conf';
      confSpan.textContent = confidencePct;

      rightDiv.appendChild(confSpan);
      item.appendChild(leftDiv);
      item.appendChild(rightDiv);
      detectionDetailsList.appendChild(item);
    });

    isProcessing = false;
  };

  // Analyse Another Image
  btnAnalyseAnother.addEventListener('click', () => {
    headerResults.classList.add('hidden');
    headerUpload.classList.remove('hidden');
    hazardsSpec.classList.remove('hidden');
    
    fileInput.value = '';
    currentFile = null;
    revokePreviewUrl();
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

    isProcessing = false;
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
