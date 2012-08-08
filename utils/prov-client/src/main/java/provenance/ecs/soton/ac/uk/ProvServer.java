package provenance.ecs.soton.ac.uk;

import org.scribe.builder.api.DefaultApi10a;
import org.scribe.model.Token;
import org.scribe.model.Verb;
import org.scribe.services.PlaintextSignatureService;

public class ProvServer extends DefaultApi10a {
	final static String HOST = "http://localhost:8000";
//	final static String HOST "http://iamvm-collabmap2.ecs.soton.ac.uk";
	
	@Override
	public Verb getRequestTokenVerb() {
		return Verb.GET;
	}

	@Override
	public String getAccessTokenEndpoint() {
		return HOST + "/oauth/access_token/";
	}

	@Override
	public String getAuthorizationUrl(Token requestToken) {
		return HOST + "/oauth/authorize?oauth_token=" + requestToken.getToken();
	}

	@Override
	public String getRequestTokenEndpoint() {
		return HOST + "/oauth/request_token/";
	}
	
}

class UpperCasePlaintextSignatureService extends PlaintextSignatureService {

	@Override
	public String getSignatureMethod() {
		return "PLAINTEXT";
	}
}