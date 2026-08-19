const form = document.getElementById("profileForm");
const savedMsg = document.getElementById("savedMsg");

// Load existing profile, if any
chrome.storage.sync.get("applicantProfile", (data) => {
  if (!data.applicantProfile) return;
  for (const [key, value] of Object.entries(data.applicantProfile)) {
    const field = form.elements[key];
    if (field) field.value = value;
  }
});

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const formData = new FormData(form);
  const profile = Object.fromEntries(formData.entries());

  // Automatically mirror programAndYear to courseSection for backend form population
  profile.courseSection = profile.programAndYear;

  chrome.storage.sync.set({ applicantProfile: profile }, () => {
    savedMsg.hidden = false;
    setTimeout(() => (savedMsg.hidden = true), 2000);
  });
});
