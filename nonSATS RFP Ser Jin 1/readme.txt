Access the Post Gap Fix 4 folder. It contains issuer wise files for 5 issuers - these are the updated final collection files for these issuers.

NOTE: After thorough discussion, it was decided that all Worldwide flight services (WFS) assets either UK or Non-UK, will be collected under IID000000002838417
WFS GLOBAL S.A.S. as website mentions this issuer as the owner of website, with everything being blocked under the original WFS Limited Issuer (any asset there too to be remapped to this issuer)

I want you to comprehensively check all these issuers against their gap reports, physical asset reports (present in subfolders under the folder to which access is given) and the reference collection file and M3 (both uploaded) to ensure that:

1. Only assets that were actually supposed to be dropped are dropped/blocked, and no genuine or correct asset has been falsely blocked (Blocking Status = ⛔ means blocked)
2. Each asset modification/correction and asset addition mentioned in gap report's missing assets and data quality sheet have been worked upon and resolved (i.e. any missing asset that has been mentioned there has been added, any quality fixes mentioned have been worked upon - the uploaded files have been processed as per reports so I believe you can check if the modification recommended for an asset is already reflecting in the file or not) (you can access gap and physical asset report for each issuer from their respective folders present in the folder provided to you)
3. Any asset that is still missing, dropped or unchanged (despite changes suggested) is properly explained (like an asset which is confirmed properly as something to be dropped, it is okay if modifications are not implemented given asset will already be dropped), for all dropped assets they are properly explained as to why they are dropped with category breakdown, etc. Sharing M3 for reference here (under construction assets need to be included here as an exception)
4. Confirm if the the issuer file (which is in sync with the comments) is in sync with the gap reports or not
5. For all active (not blocked assets) - we need to check and confirm that both latitude and longitude have atleast 5 places after decimal precision (eg: 34.12345 at least, can have move digits post decimal) - if not flag those assets
6. All files are fine sanity wise, i.e. no such instances where facility_region is present in POSTAL_CODE, etc.


Provide all 6 pointer updates issuer-wise, along with issuer-wise sets of instructions/actions required to ensure all gaps are properly fixed/addressed (with relevant facility_id/vendor_uuid or facility_name/address or reference to exact row in post gap file or gap / asset report) to close the gap and quality issues raised in gap reports through fixing or having rationale/reasoning for it.

Any doubts or queries, feel free to ask right away
