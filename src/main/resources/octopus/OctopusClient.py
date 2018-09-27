#
# Copyright 2018 XEBIALABS
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import sets, sys, time, __builtin__
from urllib import urlencode
import com.xhaus.jyson.JysonCodec as json
from xlrelease.HttpRequest import HttpRequest

HTTP_SUCCESS = sets.Set([200, 201])

class OctopusClient(object):
    
    def __init__(self, httpConnection, apiKey):
        self.httpConnection = httpConnection
        self.httpRequest = HttpRequest(httpConnection)
        self.apiKey = apiKey
        self.headers = self._get_headers()
        

    @staticmethod
    def create_client(httpConnection, apiKey):
        return OctopusClient(httpConnection, apiKey)

    def _get_headers(self):
        return {"Accept": "application/json", "Content-Type": "application/json", "X-Octopus-ApiKey": self.apiKey}

    def ping(self):
        url = '/api/serverstatus'
        response = self.httpRequest.get(url, headers=self.headers)
        if response.getStatus() in HTTP_SUCCESS: 
            data = json.loads(response.getResponse())
            print(json.dumps(data))
        else:
            self.throw_error(response)

    def start_deploy(self, projectName, releaseName, environmentName):
        releaseId = self.get_release_id(projectName, releaseName)
        return self.start_deploy_with_releaseid(releaseId, environmentName)

    def start_deploy_with_releaseid(self, releaseId, environmentName):
        environmentId = self.get_environment_id(environmentName)
        
        url = '/api/deployments'
        data = {
            "ReleaseId": releaseId,
            "EnvironmentId": environmentId,
            "TenantId": None,
            "SkipActions": [],
            "QueueTime": None,
            "QueueTimeExpiry": None,
            "FormValues": {},
            "ForcePackageDownload": False,
            "UseGuidedFailure": False,
            "SpecificMachineIds": [],
            "ExcludedMachineIds": [],
            "ForcePackageRedeployment": False
        }
        print("data = %s" % data)
        response = self.httpRequest.post(url, headers=self.headers, body=json.dumps(data))
        if response.getStatus() in HTTP_SUCCESS:
            data = json.loads(response.getResponse())
            print(json.dumps(data))
            return data["Id"]
        self.throw_error(response)

    def create_release(self, version, project, selectedPackages):
        projectId = self.get_project_id(project)
        url = '/api/releases'
        packages = json.loads(selectedPackages)
        data = {
            "Version": version,
            "ProjectId": projectId,
            "SelectedPackages": packages
        }
        response = self.httpRequest.post(url, headers=self.headers, body=json.dumps(data))
        print("HTTP_STATUS = %s" % response.getStatus())
        if response.getStatus() in HTTP_SUCCESS:
            data = json.loads(response.getResponse())
            return data["Id"]
        self.throw_error(response)

    def get_release_id(self, projectName, releaseName):
        projectId = self.get_project_id(projectName)
        url = '/api/projects/%s/releases/%s' % (projectId, releaseName)
        response = self.httpRequest.get(url, headers=self.headers)
        if response.getStatus() not in HTTP_SUCCESS:
            self.throw_error(response)
        data = json.loads(response.getResponse())
        releaseId = data["Id"]
        print "Found Release Id [%s] for name [%s]" % (releaseId, releaseName)
        return releaseId
       
    def get_environment_id(self, environment):
        url = '/api/environments/all'
        return self._get_id( url, environment )

    def get_project_id(self, project):
        url = '/api/projects/%s' % project
        # TODO remove code duplication with get_release_id
        response = self.httpRequest.get(url, headers=self.headers)
        if response.getStatus() not in HTTP_SUCCESS:
            self.throw_error(response)
        data = json.loads(response.getResponse())
        projectId = data["Id"]
        print "Found Project Id [%s] for name [%s]" % (projectId, project)
        return projectId
       
    def _get_id(self, url, objName):
        response = self.httpRequest.get(url, headers=self.headers)
        if response.getStatus() not in HTTP_SUCCESS:
            self.throw_error(response)
        data = json.loads(response.getResponse())
        for obj in data:
            if obj["Name"] == objName:
                print "Found NAME = %s/%s ID = %s" % (obj["Name"], objName, obj["Id"])
                return obj["Id"]
        sys.exit("Not Found")


    def wait_for_deploy(self, deploymentId):
        url = '/api/deployments/%s' % deploymentId
        response = self.httpRequest.get(url, headers=self.headers)
        if response.getStatus() not in HTTP_SUCCESS: 
            self.throw_error(response)
    
        deployment_details = json.loads(response.getResponse())
        taskUrl = deployment_details["Links"]["Task"]  

        time.sleep(5)
        task_details = self.get_task_details(taskUrl)

        while not task_details["IsCompleted"]:            
            task_details = self.get_task_details(taskUrl)
            time.sleep(5)

        if task_details["FinishedSuccessfully"]:
            print("Deployment finished successfully.")
        else:
            msg = "Deployment failed, errors: [%s]" % task_details["ErrorMessage"]
            print(msg)
            sys.exit(msg)
            
    def get_task_details(self, taskUrl):
        response = self.httpRequest.get(taskUrl, headers=self.headers)
        if response.getStatus() not in HTTP_SUCCESS: 
            self.throw_error(response) 
        else: 
            return json.loads(response.getResponse())
       
    def throw_error(self, response):
        msg = "Error from server, HTTP Return: %s, content %s\n" % (response.getStatus(),  response.getResponse())
        print msg
        sys.exit(msg)
