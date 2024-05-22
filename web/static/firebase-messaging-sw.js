// firebase-messaging-sw.js
importScripts('https://www.gstatic.com/firebasejs/8.2.0/firebase-app.js');
importScripts('https://www.gstatic.com/firebasejs/8.2.0/firebase-messaging.js');

firebase.initializeApp({
    apiKey: "AIzaSyBgCkpX0MDGNeK3rqVtrW5mlf17XmgPmK0",
    authDomain: "bo-chat-ad15e.firebaseapp.com",
    projectId: "bo-chat-ad15e",
    storageBucket: "bo-chat-ad15e.appspot.com",
    messagingSenderId: "578252843646",
    appId: "1:578252843646:web:a6cef4b6d90c62c022062f",
    measurementId: "G-4HCR5M4TQY"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage (function(payload) {
    console.log('[firebase-messaging-sw.js] Received background message ', payload);
  });