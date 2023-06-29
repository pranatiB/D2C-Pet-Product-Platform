// document.addEventListener("DOMContentLoaded", function() {
// 	document.querySelector('.img-btn').addEventListener('click', function()
// 	{
// 		document.querySelector('.cont').classList.toggle('s-signup')
// 	}
// );
// });
document.addEventListener('DOMContentLoaded', function() {

    // By default, load the inbox
    load_select();
    
    // Use buttons to toggle between views
    document.querySelector('#select').addEventListener('click', () => load_select());
    document.querySelector('#enter').addEventListener('click', () => load_enter());
  });

function load_select() {
  
    // Show the mailbox and hide other views
    document.querySelector('#select-address').style.display = 'block';
    document.querySelector('#enter-address').style.display = 'none';
}

function load_enter() {
  
    // Show the mailbox and hide other views
    document.querySelector('#select-address').style.display = 'none';
    document.querySelector('#enter-address').style.display = 'block';
}