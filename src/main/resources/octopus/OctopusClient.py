#
# Copyright 2017 XEBIALABS
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

    def start_deploy(self, releaseId, environment):
        environmentId = self.getEnvironmentId(environment)
        url = '/api/deployments'
        data = {
            "ReleaseId":releaseId,
            "EnvironmentId":environmentId,
            "TenantId":None,
            "SkipActions":[],
            "QueueTime":None,
            "QueueTimeExpiry":None,
            "FormValues":{},
            "ForcePackageDownload":False,
            "UseGuidedFailure":False,
            "SpecificMachineIds":[],
            "ExcludedMachineIds":[],
            "ForcePackageRedeployment":False
        }
        print("data = %s" % data)
        response = self.httpRequest.post(url, headers=self.headers, body=json.dumps(data))
        if response.getStatus() in HTTP_SUCCESS:
            data = json.loads(response.getResponse())
            print(json.dumps(data))
            return data["Id"]
        self.throw_error(response)

    def createRelease(self, version, project, selectedPackages):
        projectId = self.getProjectId(project)
        url = '/api/releases'
        packages = json.loads(selectedPackages)
        data = {
            "Version": version,
            "ProjectId": projectId,
            "SelectedPackages": packages
        }
        print("data = %s" % data)
        response = self.httpRequest.post(url, headers=self.headers, body=json.dumps(data))
        print("HTTP_SUCCESS = %s" % response.getStatus())
        if response.getStatus() in HTTP_SUCCESS:
            data = json.loads(response.getResponse())
            print("data = %s" % data)
            return data["Id"]
        self.throw_error(response)
       
    def getEnvironmentId(self, environment):
        url = '/api/environments/all'
        self.getId( url, environment )

    def getProjectId(self, project):
        url = '/api/projects/all'
        self.getId( url, project )
       
    def getId(self, url, objName):
        response = self.httpRequest.get(url, headers=self.headers)
        objId = -1
        if response.getStatus() in HTTP_SUCCESS:
            data = json.loads(response.getResponse())
            print("data = %s" % data)
            for obj in data:
                print "NAME = %s/%s ID = %s" % (obj["Name"], objName, obj["Id"])
                if obj["Name"] == objName:
                    objId = obj["Id"]
        if objId == -1:
            self.throw_error(response)
        return objId


    def wait_for_deploy(self, deploymentId):
        url = '/api/deployments/%s' % deploymentId
        response = self.httpRequest.get(url, headers=self.headers)
        if response.getStatus() not in HTTP_SUCCESS: 
            self.throw_error(response)
    
        deployment_details = json.loads(response.getResponse())
        print(json.dumps(deployment_details))
        taskUrl = deployment_details["Links"]["Task"]  

        time.sleep(5)
        task_details = self.get_task_details(taskUrl)

        while not task_details["IsCompleted"]:            
            task_details = self.get_task_details(taskUrl)
            print(json.dumps(task_details))
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