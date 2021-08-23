import demistomock as demisto
from CommonServerPython import *
import traceback
import urllib3
# Disable insecure warnings
urllib3.disable_warnings()

''' CONSTANTS '''
userUri = '/scim/v2/Users/'
groupUri = '/scim/v2/Groups/'
patchSchema = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
ERROR_CODES_TO_SKIP = [
    404
]


def build_body_request_for_update_user(old_user_data, new_user_data):
    operations = []
    for key, value in new_user_data.items():
        operation = {
            "op": "replace" if key in old_user_data.keys() else "add",
            "path": key,
            "value": [value] if key in ("emails", "phoneNumbers", "address") else value
        }
        operations.append(operation)

    data = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": operations
    }

    return data


'''CLIENT CLASS'''


class Client(BaseClient):
    """ A client class that implements logic to authenticate with the application. """

    def test(self):
        """ Tests connectivity with the application. """

        self._http_request(method='GET', url_suffix=userUri)

    def get_user(self, user_name: str) -> Optional['IAMUserAppData']:
        """ Queries the user in the application using REST API by its email, and returns an IAMUserAppData object
        that holds the user_id, username, is_active and app_data attributes given in the query response.

        :type user_name: ``str``
        :param user_name: User name of the user

        :return: An IAMUserAppData object if user exists, None otherwise.
        :rtype: ``Optional[IAMUserAppData]``
        """
        params = {
            'filter': f'userName eq "{user_name}"'  # I'm not sure email is always the user name.
        }

        res = self._http_request(
            method='GET',
            url_suffix=userUri,
            params=params
        )

        if res.get('totalResults') > 0:
            user_app_data = res.get('Resources')[0]
            user_id = user_app_data.get('id')
            username = user_app_data.get('userName')
            is_active = user_app_data.get('active')

            return IAMUserAppData(user_id, username, is_active, user_app_data)
        return None

    def create_user(self, user_data: Dict[str, Any]) -> 'IAMUserAppData':
        """ Creates a user in the application using REST API.

        :type user_data: ``Dict[str, Any]``
        :param user_data: User data in the application format

        :return: An IAMUserAppData object that contains the data of the created user in the application.
        :rtype: ``IAMUserAppData``
        """
        user_data['emails'] = [user_data['emails']]

        res = self._http_request(
            method='POST',
            url_suffix=userUri,
            json_data=user_data
        )

        user_id = res.get('id')
        is_active = res.get('active')
        username = res.get('userName')

        return IAMUserAppData(user_id, username, is_active, res)

    def update_user(self, user_id: str, new_user_data: Dict[str, Any]) -> 'IAMUserAppData':
        """ Updates a user in the application using REST API.

        :type user_id: ``str``
        :param user_id: ID of the user in the application

        :type new_user_data: ``Dict[str, Any]``
        :param new_user_data: New user data in the application format

        :return: An IAMUserAppData object that contains the data of the updated user in the application.
        :rtype: ``IAMUserAppData``
        """
        old_user_data = self._http_request(
            method='GET',
            url_suffix=userUri + user_id
        )

        res = self._http_request(
            method='PATCH',
            url_suffix=userUri + user_id,
            json_data=build_body_request_for_update_user(old_user_data, new_user_data)
        )

        is_active = res.get('active')
        username = res.get('userName')

        return IAMUserAppData(user_id, username, is_active, res)

    def enable_user(self, user_id: str) -> 'IAMUserAppData':
        """ Enables a user in the application using REST API.

        :type user_id: ``str``
        :param user_id: ID of the user in the application

        :return: An IAMUserAppData object that contains the data of the user in the application.
        :rtype: ``IAMUserAppData``
        """

        user_data = {
            "schemas": [
                "urn:ietf:params:scim:api:messages:2.0:PatchOp"
            ],
            "Operations": [
                {
                    "op": "replace",
                    "path": "active",
                    "value": "true"
                }
            ]
        }

        res = self._http_request(
            method='PATCH',
            url_suffix=userUri + user_id,
            json_data=user_data
        )

        user_id = res.get('id')
        is_active = res.get('active')
        username = res.get('userName')

        return IAMUserAppData(user_id, username, is_active, res)

    def disable_user(self, user_id: str) -> 'IAMUserAppData':
        """ Disables a user in the application using REST API.

        :type user_id: ``str``
        :param user_id: ID of the user in the application

        :return: An IAMUserAppData object that contains the data of the user in the application.
        :rtype: ``IAMUserAppData``
        """

        user_data = {
            "schemas": [
                "urn:ietf:params:scim:api:messages:2.0:PatchOp"
            ],
            "Operations": [
                {
                    "op": "replace",
                    "path": "active",
                    "value": "false"
                }
            ]
        }

        res = self._http_request(
            method='PATCH',
            url_suffix=userUri + user_id,
            json_data=user_data
        )

        user_id = res.get('id')
        is_active = res.get('active')
        username = res.get('userName')

        return IAMUserAppData(user_id, username, is_active, res)

    def http_request(self, method, url_suffix, full_url=None, params=None, data=None, headers=None):
        if headers is None:
            headers = self._headers
        full_url = full_url if full_url else urljoin(self._base_url, url_suffix)

        res = requests.request(
            method,
            full_url,
            verify=self._verify,
            headers=headers,
            params=params,
            json=data
        )
        return res

    def get_group_by_id(self, group_id):
        return self.http_request(
            method='GET',
            url_suffix=groupUri + group_id
        )

    def search_group(self, group_name):
        params = {
            'filter': f'displayName eq "{group_name}"'
        }
        return self.http_request(
            method="GET",
            url_suffix=groupUri,
            params=params
        )

    def create_group(self, data):
        return self.http_request(
            method="POST",
            url_suffix=groupUri,
            data=data
        )

    def update_group(self, group_id, data):
        return self.http_request(
            method="PATCH",
            url_suffix=groupUri + group_id,
            data=data
        )

    def delete_group(self, group_id):
        return self.http_request(
            method="DELETE",
            url_suffix=groupUri + group_id
        )

    def get_app_fields(self) -> Dict[str, Any]:
        """ Gets a dictionary of the user schema fields in the application and their description.

        :return: The user schema fields dictionary
        :rtype: ``Dict[str, str]``
        """

        uri = '/schema'
        res = self._http_request(
            method='GET',
            url_suffix=uri
        )

        fields = res.get('result', [])
        return {field.get('name'): field.get('description') for field in fields}

    @staticmethod
    def handle_exception(user_profile, e, action):
        """ Handles failed responses from the application API by setting the User Profile object with the result.
            The result entity should contain the following data:
            1. action        (``IAMActions``)       The failed action                       Required
            2. success       (``bool``)             The success status                      Optional (by default, True)
            3. skip          (``bool``)             Whether or not the command was skipped  Optional (by default, False)
            3. skip_reason   (``str``)              Skip reason                             Optional (by default, None)
            4. error_code    (``Union[str, int]``)  HTTP error code                         Optional (by default, None)
            5. error_message (``str``)              The error description                   Optional (by default, None)

            Note: This is the place to determine how to handle specific edge cases from the API, e.g.,
            when a DISABLE action was made on a user which is already disabled and therefore we can't
            perform another DISABLE action.

        :type user_profile: ``IAMUserProfile``
        :param user_profile: The user profile object

        :type e: ``Union[DemistoException, Exception]``
        :param e: The exception object - if type is DemistoException, holds the response json object (`res` attribute)

        :type action: ``IAMActions``
        :param action: An enum represents the current action (GET, UPDATE, CREATE, DISABLE or ENABLE)
        """
        if isinstance(e, DemistoException) and e.res is not None:
            error_code = e.res.status_code

            if action == IAMActions.DISABLE_USER and error_code in ERROR_CODES_TO_SKIP:
                skip_message = 'Users is already disabled or does not exist in the system.'
                user_profile.set_result(action=action,
                                        skip=True,
                                        skip_reason=skip_message)

            try:
                resp = e.res.json()
                error_message = get_error_details(resp)
            except ValueError:
                error_message = str(e)
        else:
            error_code = ''
            error_message = str(e)

        user_profile.set_result(action=action,
                                success=False,
                                error_code=error_code,
                                error_message=error_message)

        demisto.error(traceback.format_exc())


'''HELPER FUNCTIONS'''


def get_error_details(res: Dict[str, Any]) -> str:
    """ Parses the error details retrieved from the application and outputs the resulted string.

    :type res: ``Dict[str, Any]``
    :param res: The error data retrieved from the application.

    :return: The parsed error details.
    :rtype: ``str``
    """
    details = str(res.get('detail'))
    return details


class OutputContext:
    """
        Class to build a generic output and context.
    """

    def __init__(self, success=None, active=None, id=None, iden=None, username=None, email=None, errorCode=None,
                 errorMessage=None, details=None, displayName=None, members=None):
        self.instanceName = demisto.callingContext['context']['IntegrationInstance']
        self.brand = demisto.callingContext['context']['IntegrationBrand']
        self.command = demisto.command().replace('-', '_').title().replace('_', '')
        self.success = success
        self.active = active
        self.id = id
        self.iden = iden
        self.username = username
        self.email = email
        self.errorCode = errorCode
        self.errorMessage = errorMessage
        self.details = details
        self.displayName = displayName  # Used in group
        self.members = members  # Used in group
        self.data = {
            "brand": self.brand,
            "instanceName": self.instanceName,
            "success": success,
            "active": active,
            "id": iden,
            "username": username,
            "email": email,
            "errorCode": errorCode,
            "errorMessage": errorMessage,
            "details": details,
            "displayName": displayName,
            "members": members
        }


def verify_and_load_scim_data(scim):
    scim = json.loads(scim)
    if type(scim) != dict:
        raise Exception("SCIM data is not a valid JSON")
    return scim


'''COMMAND FUNCTIONS'''


def test_module(client: Client):
    """ Tests connectivity with the client. """

    client.test()
    return_results('ok')


def get_group_command(client, args):
    scim = verify_and_load_scim_data(args.get('scim'))

    group_id = scim.get('id')
    group_name = scim.get('displayName')

    if not (group_id or group_name):
        return_error("You must supply either 'id' or 'displayName' in the scim data")

    if not group_id:
        res = client.search_group(group_name)
        res_json = res.json()

        if res.status_code == 200:
            if res_json.get('totalResults') < 1:
                generic_iam_context = OutputContext(success=False, displayName=group_name, errorCode=404,
                                                    errorMessage="Group Not Found", details=res_json)

                readable_output = tableToMarkdown('AWS Get Group:', generic_iam_context.data, removeNull=True)

                return CommandResults(
                    raw_response=generic_iam_context.data,
                    outputs_prefix=generic_iam_context.command,
                    outputs_key_field='id',
                    outputs=generic_iam_context.data,
                    readable_output=readable_output
                )

            else:
                group_id = res_json['Resources'][0].get('id')
                group_name = res_json['Resources'][0].get('displayName')
                generic_iam_context = OutputContext(success=True, iden=group_id,
                                                    displayName=group_name, details=res_json)
                readable_output = tableToMarkdown('AWS Get Group:', generic_iam_context.data, removeNull=True)

                return CommandResults(
                    raw_response=generic_iam_context.data,
                    outputs_prefix=generic_iam_context.command,
                    outputs_key_field='id',
                    outputs=generic_iam_context.data,
                    readable_output=readable_output
                )

        else:
            generic_iam_context = OutputContext(success=False, displayName=group_name, iden=group_id,
                                                errorCode=res_json.get('code'),
                                                errorMessage=res_json.get('message'), details=res_json)

            readable_output = tableToMarkdown('AWS Get Group:', generic_iam_context.data, removeNull=True)

            return CommandResults(
                raw_response=generic_iam_context.data,
                outputs_prefix=generic_iam_context.command,
                outputs_key_field='id',
                outputs=generic_iam_context.data,
                readable_output=readable_output
            )

    res = client.get_group_by_id(group_id)
    res_json = res.json()

    if res.status_code == 200:
        generic_iam_context = OutputContext(success=True, iden=res_json.get('id'),
                                            displayName=res_json.get('displayName'), details=res_json)
    elif res.status_code == 404:
        generic_iam_context = OutputContext(success=False, displayName=group_name, iden=group_id, errorCode=404,
                                            errorMessage="Group Not Found", details=res_json)
    else:
        generic_iam_context = OutputContext(success=False, displayName=group_name, iden=group_id,
                                            errorCode=res_json.get('code'),
                                            errorMessage=res_json.get('message'), details=res_json)

    readable_output = tableToMarkdown('AWS Get Group:', generic_iam_context.data, removeNull=True)

    return CommandResults(
        raw_response=generic_iam_context.data,
        outputs_prefix=generic_iam_context.command,
        outputs_key_field='id',
        outputs=generic_iam_context.data,
        readable_output=readable_output
    )


def create_group_command(client, args):
    scim = verify_and_load_scim_data(args.get('scim'))
    group_name = scim.get('displayName')

    if not group_name:
        return_error("You must supply 'displayName' of the group in the scim data")

    res = client.create_group(scim)
    res_json = res.json()

    if res.status_code == 201:

        generic_iam_context = OutputContext(success=True, iden=res_json.get('id'),
                                            displayName=res_json.get('displayName'), details=res_json)
    else:
        res_json = res.json()
        generic_iam_context = OutputContext(success=False, displayName=group_name,
                                            errorCode=res_json.get('code'),
                                            errorMessage=res_json.get('message'), details=res_json)

    readable_output = tableToMarkdown('AWS Create Group:', generic_iam_context.data, removeNull=True)

    return CommandResults(
        raw_response=generic_iam_context.data,
        outputs_prefix=generic_iam_context.command,
        outputs_key_field='id',
        outputs=generic_iam_context.data,
        readable_output=readable_output
    )


def update_group_command(client, args):
    scim = verify_and_load_scim_data(args.get('scim'))

    group_id = scim.get('id')
    group_name = scim.get('displayName')

    if not group_id:
        return_error("You must supply 'id' in the scim data")

    member_ids_to_add = args.get('memberIdsToAdd')
    member_ids_to_delete = args.get('memberIdsToDelete')

    if member_ids_to_add:
        if type(member_ids_to_add) != list:
            member_ids_to_add = json.loads(member_ids_to_add)

        for member_id in member_ids_to_add:
            operation = {
                "op": "add",
                "path": "members",
                "value": [{"value": member_id}]
            }
            group_input = {'schemas': [patchSchema], 'Operations': [operation]}
            res = client.update_group(group_id, group_input)
            if res.status_code != 204:
                res_json = res.json()
                generic_iam_context = OutputContext(success=False, displayName=group_name, iden=member_id,
                                                    errorCode=res_json.get('code'),
                                                    errorMessage=res_json.get('message'), details=res_json)

                readable_output = tableToMarkdown('AWS Update Group:', generic_iam_context.data, removeNull=True)

                return CommandResults(
                    raw_response=generic_iam_context.data,
                    outputs_prefix=generic_iam_context.command,
                    outputs_key_field='id',
                    outputs=generic_iam_context.data,
                    readable_output=readable_output
                )

    if member_ids_to_delete:
        if type(member_ids_to_delete) is not list:
            member_ids_to_delete = json.loads(member_ids_to_delete)
        for member_id in member_ids_to_delete:
            operation = {
                "op": "remove",
                "path": "members",
                "value": [{"value": member_id}]
            }
            group_input = {'schemas': [patchSchema], 'Operations': [operation]}
            res = client.update_group(group_id, group_input)
            if res.status_code != 204:
                res_json = res.json()
                generic_iam_context = OutputContext(success=False, displayName=group_name, iden=member_id,
                                                    errorCode=res_json.get('code'),
                                                    errorMessage=res_json.get('message'), details=res_json)

                readable_output = tableToMarkdown('AWS Update Group:', generic_iam_context.data, removeNull=True)

                return CommandResults(
                    raw_response=generic_iam_context.data,
                    outputs_prefix=generic_iam_context.command,
                    outputs_key_field='id',
                    outputs=generic_iam_context.data,
                    readable_output=readable_output
                )

    if res.status_code == 204:
        res_json = res.headers
        generic_iam_context = OutputContext(success=True, iden=group_id, displayName=group_name, details=str(res_json))
    elif res.status_code == 404:
        res_json = res.json()
        generic_iam_context = OutputContext(success=False, iden=group_id, displayName=group_name, errorCode=404,
                                            errorMessage="Group/User Not Found or User not a member of group",
                                            details=res_json)
    else:
        res_json = res.json()
        generic_iam_context = OutputContext(success=False, iden=group_id, displayName=group_name,
                                            errorCode=res_json.get('code'), errorMessage=res_json.get('message'),
                                            details=res_json)

    readable_output = tableToMarkdown('AWS Update Group:', generic_iam_context.data, removeNull=True)

    return CommandResults(
        raw_response=generic_iam_context.data,
        outputs_prefix=generic_iam_context.command,
        outputs_key_field='id',
        outputs=generic_iam_context.data,
        readable_output=readable_output
    )


def delete_group_command(client, args):
    scim = verify_and_load_scim_data(args.get('scim'))
    group_id = scim.get('id')
    group_name = scim.get('displayName')

    if not group_id:
        return_error("The group id needs to be provided.")

    res = client.delete_group(group_id)
    if res.status_code == 204:
        res_json = res.headers
        generic_iam_context = OutputContext(success=True, iden=group_id, displayName=group_name, details=str(res_json))
    elif res.status_code == 404:
        generic_iam_context = OutputContext(success=False, iden=group_id, displayName=group_name, errorCode=404,
                                            errorMessage="Group Not Found", details=res.json())
    else:
        res_json = res.json()
        generic_iam_context = OutputContext(success=False, displayName=group_name, iden=group_id,
                                            errorCode=res_json.get('code'), errorMessage=res_json.get('message'),
                                            details=res_json)

    readable_output = tableToMarkdown('AWS Delete Group:', generic_iam_context.data, removeNull=True)

    return CommandResults(
        raw_response=generic_iam_context.data,
        outputs_prefix=generic_iam_context.command,
        outputs_key_field='id',
        outputs=generic_iam_context.data,
        readable_output=readable_output
    )


def get_mapping_fields(client: Client) -> GetMappingFieldsResponse:
    """ Creates and returns a GetMappingFieldsResponse object of the user schema in the application

    :param client: (Client) The integration Client object that implements a get_app_fields() method
    :return: (GetMappingFieldsResponse) An object that represents the user schema
    """
    app_fields = client.get_app_fields()
    incident_type_scheme = SchemeTypeMapping(type_name=IAMUserProfile.DEFAULT_INCIDENT_TYPE)

    for field, description in app_fields.items():
        incident_type_scheme.add_field(field, description)

    return GetMappingFieldsResponse([incident_type_scheme])


def main():
    user_profile = None
    params = demisto.params()
    base_url = params['url'].strip('/')
    tenant_id = params.get('tenant_id')
    url_with_tenant = f'{base_url}/{tenant_id}'
    authentication_token = params.get('authentication_token')
    mapper_in = params.get('mapper_in')
    mapper_out = params.get('mapper_out')
    verify_certificate = not params.get('insecure', False)
    proxy = params.get('proxy', False)
    command = demisto.command()
    args = demisto.args()

    is_create_enabled = params.get("create_user_enabled")
    is_enable_enabled = params.get("enable_user_enabled")
    is_disable_enabled = params.get("disable_user_enabled")
    is_update_enabled = params.get("update_user_enabled")
    create_if_not_exists = params.get("create_if_not_exists")

    iam_command = IAMCommand(is_create_enabled, is_enable_enabled, is_disable_enabled, is_update_enabled,
                             create_if_not_exists, mapper_in, mapper_out, 'username')

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {authentication_token}'
    }

    client = Client(
        base_url=url_with_tenant,
        verify=verify_certificate,
        proxy=proxy,
        headers=headers,
        ok_codes=(200, 201),
    )

    demisto.debug(f'Command being called is {command}')

    '''CRUD commands'''

    if command == 'iam-get-user':
        user_profile = iam_command.get_user(client, args)

    elif command == 'iam-create-user':
        user_profile = iam_command.create_user(client, args)

    elif command == 'iam-update-user':
        user_profile = iam_command.update_user(client, args)

    elif command == 'iam-disable-user':
        user_profile = iam_command.disable_user(client, args)

    '''non-CRUD commands'''

    if user_profile:
        return_results(user_profile)

    try:
        if command == 'test-module':
            test_module(client)

        elif command == 'iam-get-group':
            return_results(get_group_command(client, args))

        elif command == 'iam-create-group':
            return_results(create_group_command(client, args))

        elif command == 'iam-update-group':
            return_results(update_group_command(client, args))

        elif command == 'iam-delete-group':
            return_results(delete_group_command(client, args))

        elif command == 'get-mapping-fields':
            return_results(get_mapping_fields(client))

    except Exception:
        # For any other integration command exception, return an error
        return_error(f'Failed to execute {command} command. Traceback: {traceback.format_exc()}')


from IAMApiModule import * # noqa E402

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
