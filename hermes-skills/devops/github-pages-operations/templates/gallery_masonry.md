---
layout: page
title: gallery
permalink: /gallery/
nav: true
nav_order: 4
images:
  spotlight: true
artworks:
  - name: artwork_name_1
    alt: Artwork Title 1
  - name: artwork_name_2
    alt: Artwork Title 2
---

<style>
  /* Gallery Intro Banner */
  .gallery-intro {
    font-size: 0.95rem;
    line-height: 1.6;
    color: var(--global-text-color-light, #888);
    border-left: 3px solid var(--global-theme-color);
    padding-left: 1rem;
    margin: 1.5rem 0 2rem;
  }
  .gallery-intro a {
    color: var(--global-theme-color);
    text-decoration: underline;
  }

  /* Pure Visual Masonry */
  .gallery-masonry {
    column-count: 2;
    column-gap: 1.5rem;
  }
  @media (min-width: 992px) {
    .gallery-masonry {
      column-count: 3;
      column-gap: 1.5rem;
    }
  }
  @media (max-width: 600px) {
    .gallery-masonry {
      column-count: 1;
      column-gap: 0;
    }
  }

  .gallery-item {
    break-inside: avoid;
    margin-bottom: 1.5rem;
    border-radius: 12px;
    overflow: hidden;
    background-color: var(--global-card-bg-color, var(--global-bg-color));
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.12);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
    min-height: 250px;
    position: relative;
  }

  .gallery-item:hover {
    transform: translateY(-4px);
    box-shadow: 0 10px 28px rgba(0, 0, 0, 0.24);
  }

  .gallery-link {
    display: block;
    width: 100%;
    cursor: zoom-in;
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.03) 0%, rgba(0, 0, 0, 0.05) 100%);
  }

  .gallery-link picture {
    display: block;
    width: 100%;
  }

  .gallery-link img {
    width: 100%;
    height: auto;
    display: block;
    transition: transform 0.4s cubic-bezier(0.16, 1, 0.3, 1), filter 0.3s ease;
    content-visibility: auto;
  }

  .gallery-link:hover img {
    transform: scale(1.025);
  }

  /* Warning Modal & Blur state */
  #gallery-container.is-blurred {
    filter: blur(16px);
    pointer-events: none;
    user-select: none;
  }

  .warning-modal-box {
    background-color: var(--global-bg-color) !important;
    color: var(--global-text-color) !important;
    border: 1px solid var(--global-divider-color) !important;
    border-radius: 14px;
  }
</style>

<!-- Content Warning Modal (Bootstrap 4) -->
<div class="modal fade" id="galleryWarningModal" tabindex="-1" role="dialog" data-backdrop="static" data-keyboard="false" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered" role="document">
    <div class="modal-content warning-modal-box p-4 text-center shadow-lg">
      <div class="modal-body">
        <div class="mb-3">
          <i class="fa-solid fa-triangle-exclamation fa-3x text-warning"></i>
        </div>
        <h4 class="font-weight-bold mb-2">Content Warning & Disclaimer</h4>
        <p class="text-muted small mb-4">
          Galeri ini memuat karya ilustrasi visual digital.<br>
          Beberapa karya mungkin memuat tema visual tertentu.
        </p>
        <div class="d-flex justify-content-center gap-3">
          <button type="button" class="btn btn-sm btn-outline-secondary mr-2" onclick="declineWarning()">
            <i class="fa-solid fa-arrow-left mr-1"></i> Kembali
          </button>
          <button type="button" class="btn btn-sm btn-primary" onclick="acceptWarning()">
            Saya Mengerti & Lanjutkan <i class="fa-solid fa-arrow-right ml-1"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Gallery Container -->
<div id="gallery-container" class="is-blurred">
  <div class="gallery-intro">
    A showcase of digital artworks and character illustrations.
  </div>

  <!-- Pure Visual Masonry Grid -->
  <div class="gallery-masonry">
    {% for art in page.artworks %}
    <div class="gallery-item">
      <a class="spotlight gallery-link"
         href="{{ '/assets/img/art/' | append: art.name | append: '.png' | relative_url }}"
         data-theme="dark"
         data-animation="fade">
        <picture>
          <source srcset="{{ '/assets/img/art/' | append: art.name | append: '-480.webp' | relative_url }} 480w, {{ '/assets/img/art/' | append: art.name | append: '-800.webp' | relative_url }} 800w"
                  type="image/webp"
                  sizes="(max-width: 600px) 100vw, (max-width: 992px) 50vw, 33vw">
          <img src="{{ '/assets/img/art/' | append: art.name | append: '-480.webp' | relative_url }}"
               alt="{{ art.alt }}"
               loading="lazy"
               decoding="async">
        </picture>
      </a>
    </div>
    {% endfor %}
  </div>
</div>

<script>
  function showModal() {
    $('#galleryWarningModal').modal({
      backdrop: 'static',
      keyboard: false,
      show: true
    });
  }

  function acceptWarning() {
    sessionStorage.setItem('gallery_consent', 'granted');
    $('#galleryWarningModal').modal('hide');
    var container = document.getElementById('gallery-container');
    if (container) {
      container.classList.remove('is-blurred');
    }
  }

  function declineWarning() {
    window.location.href = "{{ '/' | relative_url }}";
  }

  function checkConsent() {
    if (sessionStorage.getItem('gallery_consent') === 'granted') {
      var container = document.getElementById('gallery-container');
      if (container) {
        container.classList.remove('is-blurred');
      }
    } else {
      showModal();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkConsent);
  } else {
    checkConsent();
  }
</script>
