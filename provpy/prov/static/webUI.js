function register(next){
	var location = '/prov/register';
	if(next){
		location += '?next=' + next;
	}
	document.write(location)
	window.location.href = location;
};

function go_to(url){
	window.location.href=url;
};

function view_bundle(id){
	window.location.href = '/prov/bundles/'+id;
};

function delete_bundle(id){
};

function test(event) {
	var bundle = '{"asserter":"' + document.bundle_form.asserter.value +
			   '","rec_id":"' + document.bundle_form.rec_id.value +
			   '","content":{' + document.bundle_form.content.value.replace(/(\r\n|\n|\r|\s+)/gm,"") + '}}'  
	$.ajax({
		  type: 'POST',
		  url: '/api/v0/account/',
		  data: bundle,
		  contentType: 'application/json',
		  success: function(data) {
		  	  window.location.href='/prov/home?message=The%20bundle%20was%20successfully%20created%20with%20ID%20' + data.id +'.';	
			}
		});	
	return false;
};
