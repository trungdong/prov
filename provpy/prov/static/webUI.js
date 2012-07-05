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

