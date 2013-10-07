
import os
import sys
import json
import errno
import types
import pickle
import pprint

import classad

import TaskWorker.Actions.DBSDataDiscovery as DBSDataDiscovery
import TaskWorker.Actions.Splitter as Splitter
import CRABInterface.Dagman.DagmanCreator as DagmanCreator
import TaskWorker.Actions.ASO as ASO

import WMCore.Configuration as Configuration

def megaEscape(val):
    """
    I hate this. Why are classads positively the worst
    """
    return classad.ExprTree(val).eval()

def bootstrap():
    print "Entering TaskManagerBootstrap with args: %s" % sys.argv
    command = sys.argv[1]
    if command == "PREJOB":
        return DagmanCreator.postjob(*sys.argv[2:])
    elif command == "POSTJOB":
        return DagmanCreator.prejob(*sys.argv[2:])
    elif command == "ASO":
        return ASO.async_stageout(*sys.argv[2:])

    infile, outfile = sys.argv[2:]

    adfile = os.environ["_CONDOR_JOB_AD"]
    print "Parsing classad"
    with open(adfile, "r") as fd:
        ad = classad.parseOld(fd)
    print "..done"
    in_args = []
    if infile != "None":
        with open(infile, "r") as fd:
            in_args = pickle.load(fd)

    config = Configuration.Configuration()
    config.section_("Services")
    config.Services.DBSUrl = 'http://cmsdbsprod.cern.ch/cms_dbs_prod_global/servlet/DBSServlet'
    
    ad['tm_taskname'] = ad.eval("CRAB_Workflow")
    ad['tm_split_algo'] = ad.eval("CRAB_SplitAlgo")
    ad['tm_dbs_url'] = ad.eval("CRAB_DBSUrl")
    ad['tm_input_dataset'] = ad.eval("CRAB_InputData")
    ad['tm_outfiles'] = megaEscape(ad.eval("CRAB_AdditionalOutputFiles"))
    ad['tm_tfile_outfiles'] = megaEscape(ad.eval("CRAB_TFileOutputFiles"))
    ad['tm_edm_outfiles'] = megaEscape(ad.eval("CRAB_EDMOutputFiles"))
    ad['tm_site_whitelist'] = megaEscape(ad.eval("CRAB_SiteWhitelist"))
    ad['tm_site_blacklist'] = megaEscape(ad.eval("CRAB_SiteBlacklist"))
    ad['tm_job_type'] = 'Analysis'
    print "TaskManager got this raw ad"
    print ad
    pure_ad = {}
    for key in ad:
        try:
            pure_ad[key] = ad.eval(key)
            if isinstance(pure_ad[key], classad.Value):
                del pure_ad[key]
            if isinstance(pure_ad[key], types.ListType):
                pure_ad[key] = [i.eval() for i in pure_ad[key]]
        except:
            pass
    ad = pure_ad
    ad['CRAB_AlgoArgs'] = json.loads(ad["CRAB_AlgoArgs"])
    ad['tm_split_args'] = ad["CRAB_AlgoArgs"]
    ad['tarball_location'] = os.environ.get('CRAB_TARBALL_LOCATION', '')
    print "TaskManagerBootstrap got this ad:"
    pprint.pprint(ad)
    if command == "DBS":
        task = DBSDataDiscovery.DBSDataDiscovery(config)
    elif command == "SPLIT":
        task = Splitter.Splitter(config)
        print "Got this result from the splitter"
        pprint.pprint(task)
    results = task.execute(in_args, task=ad).result
    if command == "SPLIT":
        results = DagmanCreator.create_subdag(results, task=ad)

    print results
    with open(outfile, "w") as fd:
        pickle.dump(results, fd)

    return 0

if __name__ == '__main__':
    try:
        retval = bootstrap()
        print "Ended TaskManagerBootstrap with code %s" % retval
        sys.exit(retval)
    except Exception, e:
        # TODO: make this propagate somewhere machine readable
        print "Got a fatal exception: %s" % e
        raise
        
