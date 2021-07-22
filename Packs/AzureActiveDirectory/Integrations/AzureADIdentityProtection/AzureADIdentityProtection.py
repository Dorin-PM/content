from CommonServerPython import *
import urllib3

urllib3.disable_warnings()

OUTPUTS_PREFIX = "AAD_Identity_Protection"
BASE_URL = 'https://graph.microsoft.com/beta'
REQUIRED_PERMISSIONS = (
    'offline_access',  # allows device-flow login
    'IdentityRiskEvent.Read.All',
    'IdentityRiskyUser.ReadWrite.All'
)


def parse_list(raw_response: dict, human_readable_title: str, next_link_description: str) -> CommandResults:
    """
    converts a response of Microsoft's graph search into a CommandResult object
    Note: next_link_description should be unique for every method calling parse_list
    """
    values = raw_response.get('value', [])
    readable_output = tableToMarkdown(f'{human_readable_title.title()} ({len(values)} results)',
                                      values,
                                      removeNull=True,
                                      headerTransform=pascalToSpace)
    outputs = {f'{OUTPUTS_PREFIX}.values(val.id === obj.id)': values}

    # removing whitespaces so they aren't mistakenly considered as argument separators in CLI
    next_link = raw_response.get('@odata.nextLink', '').replace(' ', '%20')
    if next_link:
        next_link_key = f'{OUTPUTS_PREFIX}.NextLink(val.Description === "{next_link_description}")'
        next_link_value = {'Description': next_link_description, 'URL': next_link}
        outputs[next_link_key] = next_link_value

    return CommandResults(outputs=outputs,
                          readable_output=readable_output,
                          raw_response=raw_response)


class AADClient:
    def __init__(self, app_id: str, subscription_id: str, verify: bool, proxy: bool, azure_ad_endpoint: str):
        if '@' in app_id:
            app_id, refresh_token = app_id.split('@')
            integration_context = get_integration_context()
            integration_context.update(current_refresh_token=refresh_token)
            set_integration_context(integration_context)

        self.ms_client = MicrosoftClient(
            self_deployed=True,
            auth_id=app_id,
            grant_type=DEVICE_CODE,
            base_url=BASE_URL,
            token_retrieval_url='https://login.microsoftonline.com/organizations/oauth2/v2.0/token',
            verify=verify,
            proxy=proxy,
            scope=' '.join(REQUIRED_PERMISSIONS),
            azure_ad_endpoint=azure_ad_endpoint
        )
        self.subscription_id = subscription_id

    def http_request(self, **kwargs):
        return self.ms_client.http_request(**kwargs)

    def query_list(self,
                   url_suffix: str,
                   limit: int,
                   filter_arguments: Optional[Dict[str, Optional[Any]]] = None,
                   filter_expression: Optional[str] = None,
                   next_link: Optional[str] = None) -> Dict:
        """ Used for querying when the result is a collection (list) of items, for example RiskyUsers. """
        if next_link:
            next_link = next_link.replace('%20', ' ')  # OData syntax can't handle '%' character
            return self.http_request(method='GET', full_url=next_link)

        else:
            params: Dict[str, Optional[Any]] = {'$top': limit}

            if filter_expression is None and filter_arguments is not None:
                filter_expression = ' and '.join([f'{key} eq \'{value}\''
                                                  for key, value in filter_arguments.items()
                                                  if value is not None])
            params['$filter'] = filter_expression
            remove_nulls_from_dictionary(params)
            return self.http_request(method='GET', url_suffix=url_suffix, params=params)

    def azure_ad_identity_protection_risk_detection_list(self,
                                                         limit: int,
                                                         filter_expression: Optional[str] = None,
                                                         next_link: Optional[str] = None,
                                                         user_id: Optional[str] = None,
                                                         user_principal_name: Optional[str] = None,
                                                         country: Optional[str] = None) -> CommandResults:
        raw_response = self.query_list(url_suffix='riskDetections',
                                       filter_arguments={
                                           'userId': user_id,
                                           'userPrincipalName': user_principal_name,
                                           'location/countryOrRegion': country
                                       },
                                       limit=limit,
                                       filter_expression=filter_expression,
                                       next_link=next_link)

        return parse_list(raw_response, human_readable_title="Risks", next_link_description="risk_detection_list")

    def azure_ad_identity_protection_risky_users_list(self,
                                                      limit: int,
                                                      filter_expression: Optional[str] = None,
                                                      next_link: Optional[str] = None,
                                                      updated_time: Optional[str] = None,
                                                      risk_level: Optional[str] = None,
                                                      risk_state: Optional[str] = None,
                                                      risk_detail: Optional[str] = None,
                                                      user_principal_name: Optional[str] = None) -> CommandResults:

        raw_response = self.query_list(
            url_suffix='RiskyUsers',
            filter_arguments={
                'riskLastUpdatedDateTime': updated_time,
                'riskLevel': risk_level,
                'riskState': risk_state,
                'riskDetail': risk_detail,
                'userPrincipalName': user_principal_name
            },
            limit=limit,
            filter_expression=filter_expression,
            next_link=next_link,
        )
        return parse_list(raw_response, human_readable_title='Risky Users', next_link_description='risky_user_list')

    def azure_ad_identity_protection_risky_users_history_list(self,
                                                              limit: int,
                                                              user_id: Optional[str] = None,
                                                              filter_expression: Optional[str] = None,
                                                              next_link: Optional[str] = None) -> CommandResults:
        raw_response = self.query_list(limit=limit, filter_expression=filter_expression,
                                       next_link=next_link, url_suffix=f'RiskyUsers/{user_id}/history')

        return parse_list(raw_response,
                          next_link_description="risky_users_history_list",
                          human_readable_title=f'Risky user history for {user_id}')

    def azure_ad_identity_protection_risky_users_confirm_compromised(self, user_ids: Union[str, List[str]]):
        self.http_request(method='POST',
                          resp_type='text',  # default json causes error, as the response is empty bytecode.
                          url_suffix='riskyUsers/confirmCompromised',
                          json_data={'userIds': argToList(user_ids)},
                          ok_codes=(204,))
        return '✅ Confirmed successfully.'  # raises exception if not successful

    def azure_ad_identity_protection_risky_users_dismiss(self, user_ids: Union[str, List[str]]):
        self.http_request(method='POST',
                          resp_type='text',  # default json causes error, as the response is empty bytecode.
                          url_suffix='riskyUsers/dismiss',
                          json_data={'userIds': argToList(user_ids)},
                          ok_codes=(204,))
        return '✅ Dismissed successfully.'  # raises exception if not successful


def azure_ad_identity_protection_risk_detection_list_command(client: AADClient, **kwargs):
    return client.azure_ad_identity_protection_risk_detection_list(**kwargs)


def azure_ad_identity_protection_risky_users_list_command(client: AADClient, **kwargs):
    return client.azure_ad_identity_protection_risky_users_list(**kwargs)


def azure_ad_identity_protection_risky_users_history_list_command(client: AADClient, **kwargs):
    return client.azure_ad_identity_protection_risky_users_history_list(**kwargs)


def azure_ad_identity_protection_risky_users_confirm_compromised_command(client: AADClient, **kwargs):
    return client.azure_ad_identity_protection_risky_users_confirm_compromised(**kwargs)


def azure_ad_identity_protection_risky_users_dismiss_command(client: AADClient, **kwargs):
    return client.azure_ad_identity_protection_risky_users_dismiss(**kwargs)


def start_auth(client: AADClient) -> CommandResults:
    result = client.ms_client.start_auth('!azure-ad-auth-complete')
    return CommandResults(readable_output=result)


def complete_auth(client: AADClient) -> str:
    client.ms_client.get_access_token()  # exception on failure
    return '✅ Authorization completed successfully.'


def test_connection(client: AADClient) -> str:
    client.ms_client.get_access_token()  # exception on failure
    return '✅ Success!'


def reset_auth() -> str:
    set_integration_context({})
    return 'Authorization was reset successfully. Run **!azure-ad-auth-start** to start the authentication process.'


def main() -> None:
    params = demisto.params()
    command = demisto.command()
    args = demisto.args()

    demisto.debug(f'Command being called is {command}')
    try:
        client = AADClient(
            app_id=params.get('app_id', ''),
            subscription_id=params.get('subscription_id', ''),
            verify=not params.get('insecure', False),
            proxy=params.get('proxy', False),
            azure_ad_endpoint=params.get('azure_ad_endpoint',
                                         'https://login.microsoftonline.com') or 'https://login.microsoftonline.com'
        )

        # auth commands
        if command == 'test-module':
            return_results('The test module is not functional, run the azure-ad-auth-start command instead.')
        elif command == 'azure-ad-auth-start':
            return_results(start_auth(client))
        elif command == 'azure-ad-auth-complete':
            return_results(complete_auth(client))
        elif command == 'azure-ad-auth-test':
            return_results(test_connection(client))
        elif command == 'azure-ad-auth-reset':
            return_results(reset_auth())

        # actual commands
        elif command == 'azure-ad-identity-protection-risks-list':
            return_results(azure_ad_identity_protection_risk_detection_list_command(client, **args))
        elif command == 'azure-ad-identity-protection-risky-user-list':
            return_results(azure_ad_identity_protection_risky_users_list_command(client, **args))
        elif command == 'azure-ad-identity-protection-risky-user-history-list':
            return_results(azure_ad_identity_protection_risky_users_history_list_command(client, **args))
        elif command == 'azure-ad-identity-protection-risky-user-confirm-compromised':
            return_results(azure_ad_identity_protection_risky_users_confirm_compromised_command(client, **args))
        elif command == 'azure-ad-identity-protection-risky-user-dismiss':
            return_results(azure_ad_identity_protection_risky_users_dismiss_command(client, **args))

        else:
            raise NotImplementedError(f'Command "{command}" is not implemented.')
    except Exception as e:
        return_error(f'Failed to execute {demisto.command()} command.\nError:\n{str(e)}', e)


from MicrosoftApiModule import *  # noqa: E402

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
