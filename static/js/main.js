// CARRUSEL
let slideIndex = 0;
const slides = document.querySelectorAll(".carousel-slide");
const prev = document.querySelector(".prev");
const next = document.querySelector(".next");

function showSlide(n) {
  slides.forEach(slide => slide.classList.remove("active"));
  slides[n].classList.add("active");
}

// Botones manuales
prev.addEventListener("click", () => {
  slideIndex = (slideIndex - 1 + slides.length) % slides.length;
  showSlide(slideIndex);
});

next.addEventListener("click", () => {
  slideIndex = (slideIndex + 1) % slides.length;
  showSlide(slideIndex);
});

// Automático
setInterval(() => {
  slideIndex = (slideIndex + 1) % slides.length;
  showSlide(slideIndex);
}, 10000); // cada 10 segundos

// GALERIA
const galeriaItems = document.querySelectorAll(".galeria-item img");
const lightbox = document.getElementById("lightbox");
const lightboxImg = document.getElementById("lightbox-img");
const closeBtn = document.querySelector(".close");

galeriaItems.forEach(img => {
  img.addEventListener("click", () => {
    lightbox.style.display = "flex";
    lightboxImg.src = img.src;
  });
});

closeBtn.addEventListener("click", () => {
  lightbox.style.display = "none";
});

lightbox.addEventListener("click", (e) => {
  if (e.target !== lightboxImg) {
    lightbox.style.display = "none";
  }
});

// REDIRECCIONES DE BOTONES DE ACCIÓN
document.querySelector(".card.arboles")?.addEventListener("click", () => {
  window.location.href = "RegistroArbol.html";
});

document.querySelector(".card.brigadas")?.addEventListener("click", () => {
  window.location.href = "RegistroBrigadas.html";
});

document.querySelector(".card.plantas")?.addEventListener("click", () => {
  window.location.href = "RegistroPlantas.html";
});